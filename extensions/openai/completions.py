<<<<<<< Updated upstream
import copy
import json
import time
from collections import deque

import tiktoken
from pydantic import ValidationError

from extensions.openai.errors import InvalidRequestError
from extensions.openai.typing import ToolDefinition
from extensions.openai.utils import debug_msg, getToolCallId, parseToolCall
from modules import shared
from modules.chat import (
    generate_chat_prompt,
    generate_chat_reply,
    load_character_memoized,
    load_instruction_template_memoized
)
from modules.presets import load_preset_memoized
from modules.text_generation import decode, encode, generate_reply


def convert_logprobs_to_tiktoken(model, logprobs):
    # more problems than it's worth.
    # try:
    #     encoder = tiktoken.encoding_for_model(model)
    #     # just pick the first one if it encodes to multiple tokens... 99.9% not required and maybe worse overall.
    #     return dict([(encoder.decode([encoder.encode(token)[0]]), prob) for token, prob in logprobs.items()])
    # except KeyError:
    #     # assume native tokens if we can't find the tokenizer
    #     return logprobs

    return logprobs


def process_parameters(body, is_legacy=False):
    generate_params = body
    max_tokens_str = 'length' if is_legacy else 'max_tokens'
    generate_params['max_new_tokens'] = body.pop(max_tokens_str)
    if generate_params['truncation_length'] == 0:
        generate_params['truncation_length'] = shared.settings['truncation_length']

    if generate_params['temperature'] == 0:
        generate_params['do_sample'] = False
        generate_params['top_k'] = 1

    if body['preset'] is not None:
        preset = load_preset_memoized(body['preset'])
        generate_params.update(preset)

    generate_params['custom_stopping_strings'] = []
    if 'stop' in body:  # str or array, max len 4 (ignored)
        if isinstance(body['stop'], str):
            generate_params['custom_stopping_strings'] = [body['stop']]
        elif isinstance(body['stop'], list):
            generate_params['custom_stopping_strings'] = body['stop']

    if shared.args.loader != 'llama.cpp':
        from transformers import LogitsProcessorList

        from modules.transformers_loader import (
            LogitsBiasProcessor,
            LogprobProcessor
        )

        logits_processor = []
        logit_bias = body.get('logit_bias', None)
        if logit_bias:  # {str: float, ...}
            logits_processor = [LogitsBiasProcessor(logit_bias)]

        logprobs = None  # coming to chat eventually
        if 'logprobs' in body:
            logprobs = body.get('logprobs', 0)  # maybe cap at topk? don't clamp 0-5.
            generate_params['logprob_proc'] = LogprobProcessor(logprobs)
            logits_processor.extend([generate_params['logprob_proc']])
        else:
            logprobs = None

        if logits_processor:  # requires logits_processor support
            generate_params['logits_processor'] = LogitsProcessorList(logits_processor)

    return generate_params


def convert_history(history):
    '''
    Chat histories in this program are in the format [message, reply].
    This function converts OpenAI histories to that format.
    '''
    chat_dialogue = []
    current_message = ""
    current_reply = ""
    user_input = ""
    user_input_last = True
    system_message = ""

    for entry in history:
        content = entry["content"]
        role = entry["role"]

        if role == "user":
            user_input = content
            user_input_last = True
            if current_message:
                chat_dialogue.append([current_message, '', ''])
                current_message = ""

            current_message = content
        elif role == "assistant":
            if "tool_calls" in entry and isinstance(entry["tool_calls"], list) and len(entry["tool_calls"]) > 0 and content.strip() == "":
                continue  # skip tool calls
            current_reply = content
            user_input_last = False
            if current_message:
                chat_dialogue.append([current_message, current_reply, ''])
                current_message = ""
                current_reply = ""
            else:
                chat_dialogue.append(['', current_reply, ''])
        elif role == "tool":
            user_input_last = False
            chat_dialogue.append(['', '', content])
        elif role == "system":
            system_message += f"\n{content}" if system_message else content

    if not user_input_last:
        user_input = ""

    return user_input, system_message, {'internal': chat_dialogue, 'visible': copy.deepcopy(chat_dialogue)}


def chat_completions_common(body: dict, is_legacy: bool = False, stream=False, prompt_only=False) -> dict:
    if body.get('functions', []):
        raise InvalidRequestError(message="functions is not supported.", param='functions')

    if body.get('function_call', ''):
        raise InvalidRequestError(message="function_call is not supported.", param='function_call')

    if 'messages' not in body:
        raise InvalidRequestError(message="messages is required", param='messages')

    tools = None
    if 'tools' in body and body['tools'] is not None and isinstance(body['tools'], list) and len(body['tools']) > 0:
        tools = validateTools(body['tools'])  # raises InvalidRequestError if validation fails

    messages = body['messages']
    for m in messages:
        if 'role' not in m:
            raise InvalidRequestError(message="messages: missing role", param='messages')
        elif m['role'] == 'function':
            raise InvalidRequestError(message="role: function is not supported.", param='messages')

        if 'content' not in m and "image_url" not in m:
            raise InvalidRequestError(message="messages: missing content", param='messages')

    # Chat Completions
    object_type = 'chat.completion' if not stream else 'chat.completion.chunk'
    created_time = int(time.time())
    cmpl_id = "chatcmpl-%d" % (int(time.time() * 1000000000))
    resp_list = 'data' if is_legacy else 'choices'

    # generation parameters
    generate_params = process_parameters(body, is_legacy=is_legacy)
    continue_ = body['continue_']

    # Instruction template
    if body['instruction_template_str']:
        instruction_template_str = body['instruction_template_str']
    elif body['instruction_template']:
        instruction_template = body['instruction_template']
        instruction_template = "Alpaca" if instruction_template == "None" else instruction_template
        instruction_template_str = load_instruction_template_memoized(instruction_template)
    else:
        instruction_template_str = shared.settings['instruction_template_str']

    chat_template_str = body['chat_template_str'] or shared.default_settings['chat_template_str']
    chat_instruct_command = body['chat_instruct_command'] or shared.default_settings['chat-instruct_command']

    # Chat character
    character = body['character'] or shared.default_settings['character']
    character = "Assistant" if character == "None" else character
    name1 = body['user_name'] or shared.default_settings['name1']
    name1, name2, _, greeting, context = load_character_memoized(character, name1, '')
    name2 = body['bot_name'] or name2
    context = body['context'] or context
    greeting = body['greeting'] or greeting
    user_bio = body['user_bio'] or ''

    # History
    user_input, custom_system_message, history = convert_history(messages)

    generate_params.update({
        'mode': body['mode'],
        'name1': name1,
        'name2': name2,
        'context': context,
        'greeting': greeting,
        'user_bio': user_bio,
        'instruction_template_str': instruction_template_str,
        'custom_system_message': custom_system_message,
        'chat_template_str': chat_template_str,
        'chat-instruct_command': chat_instruct_command,
        'tools': tools,
        'history': history,
        'stream': stream
    })

    max_tokens = generate_params['max_new_tokens']
    if max_tokens in [None, 0]:
        generate_params['max_new_tokens'] = 512
        generate_params['auto_max_new_tokens'] = True

    requested_model = generate_params.pop('model')
    logprob_proc = generate_params.pop('logprob_proc', None)

    def chat_streaming_chunk(content, chunk_tool_calls=None):
        # begin streaming
        chunk = {
            "id": cmpl_id,
            "object": object_type,
            "created": created_time,
            "model": shared.model_name,
            resp_list: [{
                "index": 0,
                "finish_reason": None,
                "delta": {'role': 'assistant', 'content': content, 'tool_calls': chunk_tool_calls},
            }],
        }

        if logprob_proc:  # not official for chat yet
            top_logprobs = convert_logprobs_to_tiktoken(model=requested_model, logprobs=logprob_proc.token_alternatives)
            chunk[resp_list][0]["logprobs"] = {'top_logprobs': [top_logprobs]}
        # else:
        #    chunk[resp_list][0]["logprobs"] = None

        return chunk

    # generate reply #######################################
    prompt = generate_chat_prompt(user_input, generate_params, _continue=continue_)
    if prompt_only:
        yield {'prompt': prompt}
        return

    if stream:
        yield chat_streaming_chunk('')

    generator = generate_chat_reply(
        user_input, generate_params, regenerate=False, _continue=continue_, loading_message=False)

    answer = ''
    seen_content = ''

    tool_calls = []
    end_last_tool_call = 0
    supported_tools = [x["function"]["name"] for x in tools] if tools is not None else None

    for a in generator:
        answer = a['internal'][-1][1]

        if supported_tools is not None:
            tool_call = parseToolCall(answer[end_last_tool_call:], supported_tools) if len(answer) > 0 else []
            if len(tool_call) > 0:
                for tc in tool_call:
                    tc["id"] = getToolCallId()
                    tc["index"] = str(len(tool_calls))
                    tc["function"]["arguments"] = json.dumps(tc["function"]["arguments"])
                    tool_calls.append(tc)
                end_last_tool_call = len(answer)

        if stream:
            len_seen = len(seen_content)
            new_content = answer[len_seen:]

            if not new_content or chr(0xfffd) in new_content:  # partial unicode character, don't send it yet.
                continue

            chunk = chat_streaming_chunk(new_content)

            seen_content = answer
            yield chunk

        # stop generation if tool_calls were generated previously
        if len(tool_calls) > 0:
            break

    token_count = len(encode(prompt)[0])
    completion_token_count = len(encode(answer)[0])
    stop_reason = "stop"
    if len(tool_calls) > 0:
        stop_reason = "tool_calls"
    if token_count + completion_token_count >= generate_params['truncation_length'] or completion_token_count >= generate_params['max_new_tokens']:
        stop_reason = "length"

    if stream:
        chunk = chat_streaming_chunk('', tool_calls)
        chunk[resp_list][0]['finish_reason'] = stop_reason
        chunk['usage'] = {
            "prompt_tokens": token_count,
            "completion_tokens": completion_token_count,
            "total_tokens": token_count + completion_token_count
        }

        yield chunk
    else:
        resp = {
            "id": cmpl_id,
            "object": object_type,
            "created": created_time,
            "model": shared.model_name,
            resp_list: [{
                "index": 0,
                "finish_reason": stop_reason,
                "message": {"role": "assistant", "content": answer},
                "tool_calls": tool_calls
            }],
            "usage": {
                "prompt_tokens": token_count,
                "completion_tokens": completion_token_count,
                "total_tokens": token_count + completion_token_count
            }
        }
        if logprob_proc:  # not official for chat yet
            top_logprobs = convert_logprobs_to_tiktoken(model=requested_model, logprobs=logprob_proc.token_alternatives)
            resp[resp_list][0]["logprobs"] = {'top_logprobs': [top_logprobs]}
        # else:
        #     resp[resp_list][0]["logprobs"] = None

        yield resp


def completions_common(body: dict, is_legacy: bool = False, stream=False):
    object_type = 'text_completion.chunk' if stream else 'text_completion'
    created_time = int(time.time())
    cmpl_id = "conv-%d" % (int(time.time() * 1000000000))
    resp_list = 'data' if is_legacy else 'choices'

    prompt_str = 'context' if is_legacy else 'prompt'

    # ... encoded as a string, array of strings, array of tokens, or array of token arrays.
    if prompt_str not in body:
        raise InvalidRequestError("Missing required input", param=prompt_str)

    # common params
    generate_params = process_parameters(body, is_legacy=is_legacy)
    max_tokens = generate_params['max_new_tokens']
    generate_params['stream'] = stream
    requested_model = generate_params.pop('model')
    logprob_proc = generate_params.pop('logprob_proc', None)
    suffix = body['suffix'] if body['suffix'] else ''
    echo = body['echo']

    if not stream:
        prompt_arg = body[prompt_str]
        if isinstance(prompt_arg, str) or (isinstance(prompt_arg, list) and isinstance(prompt_arg[0], int)):
            prompt_arg = [prompt_arg]

        resp_list_data = []
        total_completion_token_count = 0
        total_prompt_token_count = 0

        for idx, prompt in enumerate(prompt_arg, start=0):
            if isinstance(prompt[0], int):
                # token lists
                if requested_model == shared.model_name:
                    prompt = decode(prompt)[0]
                else:
                    try:
                        encoder = tiktoken.encoding_for_model(requested_model)
                        prompt = encoder.decode(prompt)
                    except KeyError:
                        prompt = decode(prompt)[0]

            prefix = prompt if echo else ''

            # generate reply #######################################
            debug_msg({'prompt': prompt, 'generate_params': generate_params})
            generator = generate_reply(prompt, generate_params, is_chat=False)
            answer = ''

            for a in generator:
                answer = a

            token_count = len(encode(prompt)[0])
            total_prompt_token_count += token_count
            completion_token_count = len(encode(answer)[0])
            total_completion_token_count += completion_token_count
            stop_reason = "stop"
            if token_count + completion_token_count >= generate_params['truncation_length'] or completion_token_count >= max_tokens:
                stop_reason = "length"

            respi = {
                "index": idx,
                "finish_reason": stop_reason,
                "text": prefix + answer + suffix,
                "logprobs": {'top_logprobs': [logprob_proc.token_alternatives]} if logprob_proc else None,
            }

            resp_list_data.extend([respi])

        resp = {
            "id": cmpl_id,
            "object": object_type,
            "created": created_time,
            "model": shared.model_name,
            resp_list: resp_list_data,
            "usage": {
                "prompt_tokens": total_prompt_token_count,
                "completion_tokens": total_completion_token_count,
                "total_tokens": total_prompt_token_count + total_completion_token_count
            }
        }

        yield resp
    else:
        prompt = body[prompt_str]
        if isinstance(prompt, list):
            if prompt and isinstance(prompt[0], int):
                try:
                    encoder = tiktoken.encoding_for_model(requested_model)
                    prompt = encoder.decode(prompt)
                except KeyError:
                    prompt = decode(prompt)[0]
            else:
                raise InvalidRequestError(message="API Batched generation not yet supported.", param=prompt_str)

        prefix = prompt if echo else ''
        token_count = len(encode(prompt)[0])

        def text_streaming_chunk(content):
            # begin streaming
            chunk = {
                "id": cmpl_id,
                "object": object_type,
                "created": created_time,
                "model": shared.model_name,
                resp_list: [{
                    "index": 0,
                    "finish_reason": None,
                    "text": content,
                    "logprobs": {'top_logprobs': [logprob_proc.token_alternatives]} if logprob_proc else None,
                }],
            }

            return chunk

        yield text_streaming_chunk(prefix)

        # generate reply #######################################
        debug_msg({'prompt': prompt, 'generate_params': generate_params})
        generator = generate_reply(prompt, generate_params, is_chat=False)

        answer = ''
        seen_content = ''
        completion_token_count = 0

        for a in generator:
            answer = a

            len_seen = len(seen_content)
            new_content = answer[len_seen:]

            if not new_content or chr(0xfffd) in new_content:  # partial unicode character, don't send it yet.
                continue

            seen_content = answer
            chunk = text_streaming_chunk(new_content)
            yield chunk

        completion_token_count = len(encode(answer)[0])
        stop_reason = "stop"
        if token_count + completion_token_count >= generate_params['truncation_length'] or completion_token_count >= max_tokens:
            stop_reason = "length"

        chunk = text_streaming_chunk(suffix)
        chunk[resp_list][0]["finish_reason"] = stop_reason
        chunk["usage"] = {
            "prompt_tokens": token_count,
            "completion_tokens": completion_token_count,
            "total_tokens": token_count + completion_token_count
        }

        yield chunk


def chat_completions(body: dict, is_legacy: bool = False) -> dict:
    generator = chat_completions_common(body, is_legacy, stream=False)
    return deque(generator, maxlen=1).pop()


def stream_chat_completions(body: dict, is_legacy: bool = False):
    for resp in chat_completions_common(body, is_legacy, stream=True):
        yield resp


def completions(body: dict, is_legacy: bool = False) -> dict:
    generator = completions_common(body, is_legacy, stream=False)
    return deque(generator, maxlen=1).pop()


def stream_completions(body: dict, is_legacy: bool = False):
    for resp in completions_common(body, is_legacy, stream=True):
        yield resp


def validateTools(tools: list[dict]):
    # Validate each tool definition in the JSON array
    valid_tools = None
    for idx in range(len(tools)):
        tool = tools[idx]
        try:
            tool_definition = ToolDefinition(**tool)
            if valid_tools is None:
                valid_tools = []
            valid_tools.append(tool)
        except ValidationError:
            raise InvalidRequestError(message=f"Invalid tool specification at index {idx}.", param='tools')

    return valid_tools
=======
import time
import yaml
import tiktoken
import torch
import torch.nn.functional as F
from math import log, exp

from transformers import LogitsProcessor, LogitsProcessorList

from modules import shared
from modules.text_generation import encode, decode, generate_reply

from extensions.openai.defaults import get_default_req_params, default, clamp
from extensions.openai.utils import end_line, debug_msg
from extensions.openai.errors import *


# Thanks to @Cypherfox [Cypherfoxy] for the logits code, blame to @matatonic
class LogitsBiasProcessor(LogitsProcessor):
    def __init__(self, logit_bias={}):
        self.logit_bias = logit_bias
        if self.logit_bias:
            self.keys = list([int(key) for key in self.logit_bias.keys()])
            values = [ self.logit_bias[str(key)] for key in self.keys ]
            self.values = torch.tensor(values, dtype=torch.float, device=shared.model.device)
            debug_msg(f"{self})")

    def __call__(self, input_ids: torch.LongTensor, logits: torch.FloatTensor) -> torch.FloatTensor:
        if self.logit_bias:
            debug_msg(logits[0, self.keys], " + ", self.values)
            logits[0, self.keys] += self.values
            debug_msg(" --> ", logits[0, self.keys])
            debug_msg(" max/min ", float(torch.max(logits[0])), float(torch.min(logits[0])))
        return logits

    def __repr__(self):
        return f"<{self.__class__.__name__}(logit_bias={self.logit_bias})>"

class LogprobProcessor(LogitsProcessor):
    def __init__(self, logprobs=None):
        self.logprobs = logprobs
        self.token_alternatives = {}

    def __call__(self, input_ids: torch.LongTensor, logits: torch.FloatTensor) -> torch.FloatTensor:
        if self.logprobs is not None:  # 0-5
            log_e_probabilities = F.log_softmax(logits, dim=1)
            top_values, top_indices = torch.topk(log_e_probabilities, k=self.logprobs+1)
            top_tokens = [ decode(tok) for tok in top_indices[0] ]
            top_probs = [ float(x) for x in top_values[0] ]
            self.token_alternatives = dict(zip(top_tokens, top_probs))
            debug_msg(repr(self))
        return logits

    def __repr__(self):
        return f"<{self.__class__.__name__}(logprobs={self.logprobs}, token_alternatives={self.token_alternatives})>"


def convert_logprobs_to_tiktoken(model, logprobs):
# more problems than it's worth.
#    try:
#        encoder = tiktoken.encoding_for_model(model)
#        # just pick the first one if it encodes to multiple tokens... 99.9% not required and maybe worse overall.
#        return dict([(encoder.decode([encoder.encode(token)[0]]), prob) for token, prob in logprobs.items()])
#    except KeyError:
#        # assume native tokens if we can't find the tokenizer
#        return logprobs
    return logprobs


def marshal_common_params(body):
    # Request Parameters
    # Try to use openai defaults or map them to something with the same intent

    req_params = get_default_req_params()

    # Common request parameters
    req_params['truncation_length'] = shared.settings['truncation_length']
    req_params['add_bos_token'] = shared.settings.get('add_bos_token', req_params['add_bos_token'])
    req_params['seed'] = shared.settings.get('seed', req_params['seed'])
    req_params['custom_stopping_strings'] = shared.settings['custom_stopping_strings']

    # OpenAI API Parameters
    # model - ignored for now, TODO: When we can reliably load a model or lora from a name only change this
    req_params['requested_model'] = body.get('model', shared.model_name)

    req_params['suffix'] = default(body, 'suffix', req_params['suffix'])
    req_params['temperature'] = clamp(default(body, 'temperature', req_params['temperature']), 0.01, 1.99)  # fixup absolute 0.0/2.0
    req_params['top_p'] = clamp(default(body, 'top_p', req_params['top_p']), 0.01, 1.0)
    n = default(body, 'n', 1)
    if n != 1:
        raise InvalidRequestError(message="Only n = 1 is supported.", param='n')

    if 'stop' in body:  # str or array, max len 4 (ignored)
        if isinstance(body['stop'], str):
            req_params['stopping_strings'] = [body['stop']]  # non-standard parameter
        elif isinstance(body['stop'], list):
            req_params['stopping_strings'] = body['stop']

    # presence_penalty - ignored
    # frequency_penalty - ignored

    # pass through unofficial params
    req_params['repetition_penalty'] = default(body, 'repetition_penalty', req_params['repetition_penalty'])
    req_params['encoder_repetition_penalty'] = default(body, 'encoder_repetition_penalty', req_params['encoder_repetition_penalty'])

    # user - ignored

    logits_processor = []
    logit_bias = body.get('logit_bias', None)
    if logit_bias:  # {str: float, ...}
        # XXX convert tokens from tiktoken based on requested model
        # Ex.: 'logit_bias': {'1129': 100, '11442': 100, '16243': 100}
        try:
            encoder = tiktoken.encoding_for_model(req_params['requested_model'])
            new_logit_bias = {}
            for logit, bias in logit_bias.items():
                for x in encode(encoder.decode([int(logit)]), add_special_tokens=False)[0]:
                    if int(x) in [0, 1, 2, 29871]: # XXX LLAMA tokens
                        continue
                    new_logit_bias[str(int(x))] = bias
            debug_msg('logit_bias_map', logit_bias, '->', new_logit_bias)
            logit_bias = new_logit_bias
        except KeyError:
            pass  # assume native tokens if we can't find the tokenizer

        logits_processor = [LogitsBiasProcessor(logit_bias)]

    logprobs = None  # coming to chat eventually
    if 'logprobs' in body:
        logprobs = default(body, 'logprobs', 0)  # maybe cap at topk? don't clamp 0-5.
        req_params['logprob_proc'] = LogprobProcessor(logprobs)
        logits_processor.extend([req_params['logprob_proc']])
    else:
        logprobs = None

    if logits_processor:  # requires logits_processor support
        req_params['logits_processor'] = LogitsProcessorList(logits_processor)

    return req_params


def messages_to_prompt(body: dict, req_params: dict, max_tokens):
    # functions
    if body.get('functions', []):  # chat only
        raise InvalidRequestError(message="functions is not supported.", param='functions')
    if body.get('function_call', ''):  # chat only, 'none', 'auto', {'name': 'func'}
        raise InvalidRequestError(message="function_call is not supported.", param='function_call')

    if not 'messages' in body:
        raise InvalidRequestError(message="messages is required", param='messages')

    messages = body['messages']

    role_formats = {
        'user': 'User: {message}\n',
        'assistant': 'Assistant: {message}\n',
        'system': '{message}',
        'context': 'You are a helpful assistant. Answer as concisely as possible.\nUser: I want your assistance.\nAssistant: Sure! What can I do for you?',
        'prompt': 'Assistant:',
    }

    if not 'stopping_strings' in req_params:
        req_params['stopping_strings'] = []

    # Instruct models can be much better
    if shared.settings['instruction_template']:
        try:
            instruct = yaml.safe_load(open(f"characters/instruction-following/{shared.settings['instruction_template']}.yaml", 'r'))

            template = instruct['turn_template']
            system_message_template = "{message}"
            system_message_default = instruct.get('context', '') # can be missing
            bot_start = template.find('<|bot|>')  # So far, 100% of instruction templates have this token
            user_message_template = template[:bot_start].replace('<|user-message|>', '{message}').replace('<|user|>', instruct.get('user', ''))
            bot_message_template = template[bot_start:].replace('<|bot-message|>', '{message}').replace('<|bot|>', instruct.get('bot', ''))
            bot_prompt = bot_message_template[:bot_message_template.find('{message}')].rstrip(' ')

            role_formats = {
                'user': user_message_template,
                'assistant': bot_message_template,
                'system': system_message_template,
                'context': system_message_default,
                'prompt': bot_prompt,
            }

            if 'Alpaca' in shared.settings['instruction_template']:
                req_params['stopping_strings'].extend(['\n###'])
            elif instruct['user']:  # WizardLM and some others have no user prompt.
                req_params['stopping_strings'].extend(['\n' + instruct['user'], instruct['user']])

            debug_msg(f"Loaded instruction role format: {shared.settings['instruction_template']}")

        except Exception as e:
            req_params['stopping_strings'].extend(['\nUser:', 'User:'])  # XXX User: prompt here also

            print(f"Exception: When loading characters/instruction-following/{shared.settings['instruction_template']}.yaml: {repr(e)}")
            print("Warning: Loaded default instruction-following template for model.")

    else:
        req_params['stopping_strings'].extend(['\nUser:', 'User:'])  # XXX User: prompt here also
        print("Warning: Loaded default instruction-following template for model.")

    system_msgs = []
    chat_msgs = []

    # You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible. Knowledge cutoff: {knowledge_cutoff} Current date: {current_date}
    context_msg = role_formats['system'].format(message=role_formats['context']) if role_formats['context'] else ''
    context_msg = end_line(context_msg)

    # Maybe they sent both? This is not documented in the API, but some clients seem to do this.
    if 'prompt' in body:
        context_msg = end_line(role_formats['system'].format(message=body['prompt'])) + context_msg

    for m in messages:
        if 'role' not in m:
            raise InvalidRequestError(message="messages: missing role", param='messages')
        if 'content' not in m:
            raise InvalidRequestError(message="messages: missing content", param='messages')
        
        role = m['role']
        content = m['content']
        # name = m.get('name', None)
        # function_call = m.get('function_call', None) # user name or function name with output in content
        msg = role_formats[role].format(message=content)
        if role == 'system':
            system_msgs.extend([msg])
        elif role == 'function':
            raise InvalidRequestError(message="role: function is not supported.", param='messages')
        else:
            chat_msgs.extend([msg])

    system_msg = '\n'.join(system_msgs)
    system_msg = end_line(system_msg)

    prompt = system_msg + context_msg + ''.join(chat_msgs) + role_formats['prompt']

    token_count = len(encode(prompt)[0])

    if token_count >= req_params['truncation_length']:
        err_msg = f"This model maximum context length is {req_params['truncation_length']} tokens. However, your messages resulted in over {token_count} tokens."
        raise InvalidRequestError(message=err_msg, param='messages')

    if max_tokens > 0 and token_count + max_tokens > req_params['truncation_length']:
        err_msg = f"This model maximum context length is {req_params['truncation_length']} tokens. However, your messages resulted in over {token_count} tokens and max_tokens is {max_tokens}."
        print(f"Warning: ${err_msg}")
        # raise InvalidRequestError(message=err_msg, params='max_tokens')

    return prompt, token_count


def chat_completions(body: dict, is_legacy: bool = False) -> dict:
    # Chat Completions
    object_type = 'chat.completions'
    created_time = int(time.time())
    cmpl_id = "chatcmpl-%d" % (int(time.time() * 1000000000))
    resp_list = 'data' if is_legacy else 'choices'

    # common params
    req_params = marshal_common_params(body)
    req_params['stream'] = False
    requested_model = req_params.pop('requested_model')
    logprob_proc = req_params.pop('logprob_proc', None)
    req_params['top_k'] = 20  # There is no best_of/top_k param for chat, but it is much improved with a higher top_k.

    # chat default max_tokens is 'inf', but also flexible
    max_tokens = 0
    max_tokens_str = 'length' if is_legacy else 'max_tokens'
    if max_tokens_str in body:
        max_tokens = default(body, max_tokens_str, req_params['truncation_length'])
        req_params['max_new_tokens'] = max_tokens
    else:
        req_params['max_new_tokens'] = req_params['truncation_length']

    # format the prompt from messages
    prompt, token_count = messages_to_prompt(body, req_params, max_tokens)  # updates req_params['stopping_strings']

    # set real max, avoid deeper errors
    if req_params['max_new_tokens'] + token_count >= req_params['truncation_length']:
        req_params['max_new_tokens'] = req_params['truncation_length'] - token_count

    stopping_strings = req_params.pop('stopping_strings', [])

    # generate reply #######################################
    debug_msg({'prompt': prompt, 'req_params': req_params})
    generator = generate_reply(prompt, req_params, stopping_strings=stopping_strings, is_chat=False)

    answer = ''
    for a in generator:
        answer = a

    # strip extra leading space off new generated content
    if answer and answer[0] == ' ':
        answer = answer[1:]

    completion_token_count = len(encode(answer)[0])
    stop_reason = "stop"
    if token_count + completion_token_count >= req_params['truncation_length'] or completion_token_count >= req_params['max_new_tokens']:
        stop_reason = "length"

    resp = {
        "id": cmpl_id,
        "object": object_type,
        "created": created_time,
        "model": shared.model_name,  # TODO: add Lora info?
        resp_list: [{
            "index": 0,
            "finish_reason": stop_reason,
            "message": {"role": "assistant", "content": answer}
        }],
        "usage": {
            "prompt_tokens": token_count,
            "completion_tokens": completion_token_count,
            "total_tokens": token_count + completion_token_count
        }
    }
    if logprob_proc:  # not official for chat yet
        top_logprobs = convert_logprobs_to_tiktoken(model=requested_model, logprobs=logprob_proc.token_alternatives)
        resp[resp_list][0]["logprobs"] = {'top_logprobs': [top_logprobs]}
    # else:
    #     resp[resp_list][0]["logprobs"] = None

    return resp


# generator
def stream_chat_completions(body: dict, is_legacy: bool = False):

    # Chat Completions
    stream_object_type = 'chat.completions.chunk'
    created_time = int(time.time())
    cmpl_id = "chatcmpl-%d" % (int(time.time() * 1000000000))
    resp_list = 'data' if is_legacy else 'choices'

    # common params
    req_params = marshal_common_params(body)
    req_params['stream'] = True
    requested_model = req_params.pop('requested_model')
    logprob_proc = req_params.pop('logprob_proc', None)
    req_params['top_k'] = 20  # There is no best_of/top_k param for chat, but it is much improved with a higher top_k.

    # chat default max_tokens is 'inf', but also flexible
    max_tokens = 0
    max_tokens_str = 'length' if is_legacy else 'max_tokens'
    if max_tokens_str in body:
        max_tokens = default(body, max_tokens_str, req_params['truncation_length'])
        req_params['max_new_tokens'] = max_tokens
    else:
        req_params['max_new_tokens'] = req_params['truncation_length']

    # format the prompt from messages
    prompt, token_count = messages_to_prompt(body, req_params, max_tokens)  # updates req_params['stopping_strings']

    # set real max, avoid deeper errors
    if req_params['max_new_tokens'] + token_count >= req_params['truncation_length']:
        req_params['max_new_tokens'] = req_params['truncation_length'] - token_count

    def chat_streaming_chunk(content):
        # begin streaming
        chunk = {
            "id": cmpl_id,
            "object": stream_object_type,
            "created": created_time,
            "model": shared.model_name,
            resp_list: [{
                "index": 0,
                "finish_reason": None,
                # So yeah... do both methods? delta and messages.
                "message": {'role': 'assistant', 'content': content},
                "delta": {'role': 'assistant', 'content': content},
            }],
        }

        if logprob_proc:  # not official for chat yet
            top_logprobs = convert_logprobs_to_tiktoken(model=requested_model, logprobs=logprob_proc.token_alternatives)
            chunk[resp_list][0]["logprobs"] = {'top_logprobs': [top_logprobs]}
        # else:
        #    chunk[resp_list][0]["logprobs"] = None
        return chunk

    yield chat_streaming_chunk('')

    # generate reply #######################################
    debug_msg({'prompt': prompt, 'req_params': req_params})

    stopping_strings = req_params.pop('stopping_strings', [])

    generator = generate_reply(prompt, req_params, stopping_strings=stopping_strings, is_chat=False)

    answer = ''
    seen_content = ''
    completion_token_count = 0

    for a in generator:
        answer = a

        len_seen = len(seen_content)
        new_content = answer[len_seen:]

        if not new_content or chr(0xfffd) in new_content:  # partial unicode character, don't send it yet.
            continue

        seen_content = answer

        # strip extra leading space off new generated content
        if len_seen == 0 and new_content[0] == ' ':
            new_content = new_content[1:]

        chunk = chat_streaming_chunk(new_content)

        yield chunk

    # to get the correct token_count, strip leading space if present
    if answer and answer[0] == ' ':
        answer = answer[1:]

    completion_token_count = len(encode(answer)[0])
    stop_reason = "stop"
    if token_count + completion_token_count >= req_params['truncation_length'] or completion_token_count >= req_params['max_new_tokens']:
        stop_reason = "length"

    chunk = chat_streaming_chunk('')
    chunk[resp_list][0]['finish_reason'] = stop_reason
    chunk['usage'] = {
        "prompt_tokens": token_count,
        "completion_tokens": completion_token_count,
        "total_tokens": token_count + completion_token_count
    }

    yield chunk


def completions(body: dict, is_legacy: bool = False):
    # Legacy
    # Text Completions
    object_type = 'text_completion'
    created_time = int(time.time())
    cmpl_id = "conv-%d" % (int(time.time() * 1000000000))
    resp_list = 'data' if is_legacy else 'choices'

    # ... encoded as a string, array of strings, array of tokens, or array of token arrays.
    prompt_str = 'context' if is_legacy else 'prompt'
    if not prompt_str in body:
        raise InvalidRequestError("Missing required input", param=prompt_str)

    prompt_arg = body[prompt_str]
    if isinstance(prompt_arg, str) or (isinstance(prompt_arg, list) and isinstance(prompt_arg[0], int)):
        prompt_arg = [prompt_arg]

    # common params
    req_params = marshal_common_params(body)
    req_params['stream'] = False
    max_tokens_str = 'length' if is_legacy else 'max_tokens'
    max_tokens = default(body, max_tokens_str, req_params['max_new_tokens'])
    req_params['max_new_tokens'] = max_tokens
    requested_model = req_params.pop('requested_model')
    logprob_proc = req_params.pop('logprob_proc', None)
    stopping_strings = req_params.pop('stopping_strings', [])
    #req_params['suffix'] = default(body, 'suffix', req_params['suffix'])
    req_params['echo'] = default(body, 'echo', req_params['echo'])
    req_params['top_k'] = default(body, 'best_of', req_params['top_k'])

    resp_list_data = []
    total_completion_token_count = 0
    total_prompt_token_count = 0

    for idx, prompt in enumerate(prompt_arg, start=0):
        if isinstance(prompt[0], int):
            # token lists
            if requested_model == shared.model_name:
                prompt = decode(prompt)[0]
            else:
                try:
                    encoder = tiktoken.encoding_for_model(requested_model)
                    prompt = encoder.decode(prompt)
                except KeyError:
                    prompt = decode(prompt)[0]

        token_count = len(encode(prompt)[0])
        total_prompt_token_count += token_count

        if token_count + max_tokens > req_params['truncation_length']:
            err_msg = f"The token count of your prompt ({token_count}) plus max_tokens ({max_tokens}) cannot exceed the model's context length ({req_params['truncation_length']})."
            # print(f"Warning: ${err_msg}")
            raise InvalidRequestError(message=err_msg, param=max_tokens_str)

        # generate reply #######################################
        debug_msg({'prompt': prompt, 'req_params': req_params})
        generator = generate_reply(prompt, req_params, stopping_strings=stopping_strings, is_chat=False)
        answer = ''

        for a in generator:
            answer = a

        # strip extra leading space off new generated content
        if answer and answer[0] == ' ':
            answer = answer[1:]

        completion_token_count = len(encode(answer)[0])
        total_completion_token_count += completion_token_count
        stop_reason = "stop"
        if token_count + completion_token_count >= req_params['truncation_length'] or completion_token_count >= max_tokens:
            stop_reason = "length"

        respi = {
            "index": idx,
            "finish_reason": stop_reason,
            "text": answer,
            "logprobs": {'top_logprobs': [logprob_proc.token_alternatives]} if logprob_proc else None,
        }

        resp_list_data.extend([respi])

    resp = {
        "id": cmpl_id,
        "object": object_type,
        "created": created_time,
        "model": shared.model_name,  # TODO: add Lora info?
        resp_list: resp_list_data,
        "usage": {
            "prompt_tokens": total_prompt_token_count,
            "completion_tokens": total_completion_token_count,
            "total_tokens": total_prompt_token_count + total_completion_token_count
        }
    }

    return resp


# generator
def stream_completions(body: dict, is_legacy: bool = False):
    # Legacy
    # Text Completions
    # object_type = 'text_completion'
    stream_object_type = 'text_completion.chunk'
    created_time = int(time.time())
    cmpl_id = "conv-%d" % (int(time.time() * 1000000000))
    resp_list = 'data' if is_legacy else 'choices'

    # ... encoded as a string, array of strings, array of tokens, or array of token arrays.
    prompt_str = 'context' if is_legacy else 'prompt'
    if not prompt_str in body:
        raise InvalidRequestError("Missing required input", param=prompt_str)

    prompt = body[prompt_str]
    if isinstance(prompt, list):
        if prompt and isinstance(prompt[0], int):
            try:
                encoder = tiktoken.encoding_for_model(requested_model)
                prompt = encoder.decode(prompt)
            except KeyError:
                prompt = decode(prompt)[0]
        else:
            raise InvalidRequestError(message="API Batched generation not yet supported.", param=prompt_str)

    # common params
    req_params = marshal_common_params(body)
    req_params['stream'] = True
    max_tokens_str = 'length' if is_legacy else 'max_tokens'
    max_tokens = default(body, max_tokens_str, req_params['max_new_tokens'])
    req_params['max_new_tokens'] = max_tokens
    requested_model = req_params.pop('requested_model')
    logprob_proc = req_params.pop('logprob_proc', None)
    stopping_strings = req_params.pop('stopping_strings', [])
    #req_params['suffix'] = default(body, 'suffix', req_params['suffix'])
    req_params['echo'] = default(body, 'echo', req_params['echo'])
    req_params['top_k'] = default(body, 'best_of', req_params['top_k'])

    token_count = len(encode(prompt)[0])

    if token_count + max_tokens > req_params['truncation_length']:
        err_msg = f"The token count of your prompt ({token_count}) plus max_tokens ({max_tokens}) cannot exceed the model's context length ({req_params['truncation_length']})."
        # print(f"Warning: ${err_msg}")
        raise InvalidRequestError(message=err_msg, param=max_tokens_str)

    def text_streaming_chunk(content):
        # begin streaming
        chunk = {
            "id": cmpl_id,
            "object": stream_object_type,
            "created": created_time,
            "model": shared.model_name,
            resp_list: [{
                "index": 0,
                "finish_reason": None,
                "text": content,
                "logprobs": {'top_logprobs': [logprob_proc.token_alternatives]} if logprob_proc else None,
            }],
        }

        return chunk

    yield text_streaming_chunk('')

    # generate reply #######################################
    debug_msg({'prompt': prompt, 'req_params': req_params})
    generator = generate_reply(prompt, req_params, stopping_strings=stopping_strings, is_chat=False)

    answer = ''
    seen_content = ''
    completion_token_count = 0

    for a in generator:
        answer = a

        len_seen = len(seen_content)
        new_content = answer[len_seen:]

        if not new_content or chr(0xfffd) in new_content:  # partial unicode character, don't send it yet.
            continue

        seen_content = answer

        # strip extra leading space off new generated content
        if len_seen == 0 and new_content[0] == ' ':
            new_content = new_content[1:]

        chunk = text_streaming_chunk(new_content)

        yield chunk

    # to get the correct count, we strip the leading space if present
    if answer and answer[0] == ' ':
        answer = answer[1:]

    completion_token_count = len(encode(answer)[0])
    stop_reason = "stop"
    if token_count + completion_token_count >= req_params['truncation_length'] or completion_token_count >= max_tokens:
        stop_reason = "length"

    chunk = text_streaming_chunk('')
    chunk[resp_list][0]["finish_reason"] = stop_reason
    chunk["usage"] = {
        "prompt_tokens": token_count,
        "completion_tokens": completion_token_count,
        "total_tokens": token_count + completion_token_count
    }

    yield chunk
>>>>>>> Stashed changes
