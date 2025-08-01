<<<<<<< Updated upstream
import argparse
import copy
import os
import shlex
import sys
from collections import OrderedDict
from pathlib import Path

import yaml

from modules.logging_colors import logger
from modules.presets import default_preset

# Model variables
model = None
tokenizer = None
model_name = 'None'
is_seq2seq = False
model_dirty_from_training = False
lora_names = []

# Generation variables
stop_everything = False
generation_lock = None
processing_message = ''

# UI variables
gradio = {}
persistent_interface_state = {}
need_restart = False

# Parser copied from https://github.com/vladmandic/automatic
parser = argparse.ArgumentParser(description="Text generation web UI", conflict_handler='resolve', add_help=True, formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=55, indent_increment=2, width=200))

# Basic settings
group = parser.add_argument_group('Basic settings')
group.add_argument('--multi-user', action='store_true', help='Multi-user mode. Chat histories are not saved or automatically loaded. Warning: this is likely not safe for sharing publicly.')
group.add_argument('--model', type=str, help='Name of the model to load by default.')
group.add_argument('--lora', type=str, nargs='+', help='The list of LoRAs to load. If you want to load more than one LoRA, write the names separated by spaces.')
group.add_argument('--model-dir', type=str, default='user_data/models', help='Path to directory with all the models.')
group.add_argument('--lora-dir', type=str, default='user_data/loras', help='Path to directory with all the loras.')
group.add_argument('--model-menu', action='store_true', help='Show a model menu in the terminal when the web UI is first launched.')
group.add_argument('--settings', type=str, help='Load the default interface settings from this yaml file. See user_data/settings-template.yaml for an example. If you create a file called user_data/settings.yaml, this file will be loaded by default without the need to use the --settings flag.')
group.add_argument('--extensions', type=str, nargs='+', help='The list of extensions to load. If you want to load more than one extension, write the names separated by spaces.')
group.add_argument('--verbose', action='store_true', help='Print the prompts to the terminal.')
group.add_argument('--idle-timeout', type=int, default=0, help='Unload model after this many minutes of inactivity. It will be automatically reloaded when you try to use it again.')

# Model loader
group = parser.add_argument_group('Model loader')
group.add_argument('--loader', type=str, help='Choose the model loader manually, otherwise, it will get autodetected. Valid options: Transformers, llama.cpp, ExLlamav3_HF, ExLlamav2_HF, ExLlamav2, TensorRT-LLM.')

# Transformers/Accelerate
group = parser.add_argument_group('Transformers/Accelerate')
group.add_argument('--cpu', action='store_true', help='Use the CPU to generate text. Warning: Training on CPU is extremely slow.')
group.add_argument('--cpu-memory', type=float, default=0, help='Maximum CPU memory in GiB. Use this for CPU offloading.')
group.add_argument('--disk', action='store_true', help='If the model is too large for your GPU(s) and CPU combined, send the remaining layers to the disk.')
group.add_argument('--disk-cache-dir', type=str, default='user_data/cache', help='Directory to save the disk cache to. Defaults to "user_data/cache".')
group.add_argument('--load-in-8bit', action='store_true', help='Load the model with 8-bit precision (using bitsandbytes).')
group.add_argument('--bf16', action='store_true', help='Load the model with bfloat16 precision. Requires NVIDIA Ampere GPU.')
group.add_argument('--no-cache', action='store_true', help='Set use_cache to False while generating text. This reduces VRAM usage slightly, but it comes at a performance cost.')
group.add_argument('--trust-remote-code', action='store_true', help='Set trust_remote_code=True while loading the model. Necessary for some models.')
group.add_argument('--force-safetensors', action='store_true', help='Set use_safetensors=True while loading the model. This prevents arbitrary code execution.')
group.add_argument('--no_use_fast', action='store_true', help='Set use_fast=False while loading the tokenizer (it\'s True by default). Use this if you have any problems related to use_fast.')
group.add_argument('--attn-implementation', type=str, default='sdpa', metavar="IMPLEMENTATION", help='Attention implementation. Valid options: sdpa, eager, flash_attention_2.')

# bitsandbytes 4-bit
group = parser.add_argument_group('bitsandbytes 4-bit')
group.add_argument('--load-in-4bit', action='store_true', help='Load the model with 4-bit precision (using bitsandbytes).')
group.add_argument('--use_double_quant', action='store_true', help='use_double_quant for 4-bit.')
group.add_argument('--compute_dtype', type=str, default='float16', help='compute dtype for 4-bit. Valid options: bfloat16, float16, float32.')
group.add_argument('--quant_type', type=str, default='nf4', help='quant_type for 4-bit. Valid options: nf4, fp4.')

# llama.cpp
group = parser.add_argument_group('llama.cpp')
group.add_argument('--flash-attn', action='store_true', help='Use flash-attention.')
group.add_argument('--threads', type=int, default=0, help='Number of threads to use.')
group.add_argument('--threads-batch', type=int, default=0, help='Number of threads to use for batches/prompt processing.')
group.add_argument('--batch-size', type=int, default=256, help='Maximum number of prompt tokens to batch together when calling llama_eval.')
group.add_argument('--no-mmap', action='store_true', help='Prevent mmap from being used.')
group.add_argument('--mlock', action='store_true', help='Force the system to keep the model in RAM.')
group.add_argument('--gpu-layers', '--n-gpu-layers', type=int, default=256, metavar='N', help='Number of layers to offload to the GPU.')
group.add_argument('--tensor-split', type=str, default=None, help='Split the model across multiple GPUs. Comma-separated list of proportions. Example: 60,40.')
group.add_argument('--numa', action='store_true', help='Activate NUMA task allocation for llama.cpp.')
group.add_argument('--no-kv-offload', action='store_true', help='Do not offload the  K, Q, V to the GPU. This saves VRAM but reduces the performance.')
group.add_argument('--row-split', action='store_true', help='Split the model by rows across GPUs. This may improve multi-gpu performance.')
group.add_argument('--extra-flags', type=str, default=None, help='Extra flags to pass to llama-server. Format: "flag1=value1,flag2,flag3=value3". Example: "override-tensor=exps=CPU"')
group.add_argument('--streaming-llm', action='store_true', help='Activate StreamingLLM to avoid re-evaluating the entire prompt when old messages are removed.')

# Cache
group = parser.add_argument_group('Context and cache')
group.add_argument('--ctx-size', '--n_ctx', '--max_seq_len', type=int, default=8192, metavar='N', help='Context size in tokens.')
group.add_argument('--cache-type', '--cache_type', type=str, default='fp16', metavar='N', help='KV cache type; valid options: llama.cpp - fp16, q8_0, q4_0; ExLlamaV2 - fp16, fp8, q8, q6, q4; ExLlamaV3 - fp16, q2 to q8 (can specify k_bits and v_bits separately, e.g. q4_q8).')

# Speculative decoding
group = parser.add_argument_group('Speculative decoding')
group.add_argument('--model-draft', type=str, default=None, help='Path to the draft model for speculative decoding.')
group.add_argument('--draft-max', type=int, default=4, help='Number of tokens to draft for speculative decoding.')
group.add_argument('--gpu-layers-draft', type=int, default=256, help='Number of layers to offload to the GPU for the draft model.')
group.add_argument('--device-draft', type=str, default=None, help='Comma-separated list of devices to use for offloading the draft model. Example: CUDA0,CUDA1')
group.add_argument('--ctx-size-draft', type=int, default=0, help='Size of the prompt context for the draft model. If 0, uses the same as the main model.')

# ExLlamaV2
group = parser.add_argument_group('ExLlamaV2')
group.add_argument('--gpu-split', type=str, help='Comma-separated list of VRAM (in GB) to use per GPU device for model layers. Example: 20,7,7.')
group.add_argument('--autosplit', action='store_true', help='Autosplit the model tensors across the available GPUs. This causes --gpu-split to be ignored.')
group.add_argument('--cfg-cache', action='store_true', help='ExLlamav2_HF: Create an additional cache for CFG negative prompts. Necessary to use CFG with that loader.')
group.add_argument('--no_flash_attn', action='store_true', help='Force flash-attention to not be used.')
group.add_argument('--no_xformers', action='store_true', help='Force xformers to not be used.')
group.add_argument('--no_sdpa', action='store_true', help='Force Torch SDPA to not be used.')
group.add_argument('--num_experts_per_token', type=int, default=2, metavar='N', help='Number of experts to use for generation. Applies to MoE models like Mixtral.')
group.add_argument('--enable_tp', action='store_true', help='Enable Tensor Parallelism (TP) in ExLlamaV2.')

# TensorRT-LLM
group = parser.add_argument_group('TensorRT-LLM')
group.add_argument('--cpp-runner', action='store_true', help='Use the ModelRunnerCpp runner, which is faster than the default ModelRunner but doesn\'t support streaming yet.')

# DeepSpeed
group = parser.add_argument_group('DeepSpeed')
group.add_argument('--deepspeed', action='store_true', help='Enable the use of DeepSpeed ZeRO-3 for inference via the Transformers integration.')
group.add_argument('--nvme-offload-dir', type=str, help='DeepSpeed: Directory to use for ZeRO-3 NVME offloading.')
group.add_argument('--local_rank', type=int, default=0, help='DeepSpeed: Optional argument for distributed setups.')

# RoPE
group = parser.add_argument_group('RoPE')
group.add_argument('--alpha_value', type=float, default=1, help='Positional embeddings alpha factor for NTK RoPE scaling. Use either this or compress_pos_emb, not both.')
group.add_argument('--rope_freq_base', type=int, default=0, help='If greater than 0, will be used instead of alpha_value. Those two are related by rope_freq_base = 10000 * alpha_value ^ (64 / 63).')
group.add_argument('--compress_pos_emb', type=int, default=1, help="Positional embeddings compression factor. Should be set to (context length) / (model\'s original context length). Equal to 1/rope_freq_scale.")

# Gradio
group = parser.add_argument_group('Gradio')
group.add_argument('--listen', action='store_true', help='Make the web UI reachable from your local network.')
group.add_argument('--listen-port', type=int, help='The listening port that the server will use.')
group.add_argument('--listen-host', type=str, help='The hostname that the server will use.')
group.add_argument('--share', action='store_true', help='Create a public URL. This is useful for running the web UI on Google Colab or similar.')
group.add_argument('--auto-launch', action='store_true', default=False, help='Open the web UI in the default browser upon launch.')
group.add_argument('--gradio-auth', type=str, help='Set Gradio authentication password in the format "username:password". Multiple credentials can also be supplied with "u1:p1,u2:p2,u3:p3".', default=None)
group.add_argument('--gradio-auth-path', type=str, help='Set the Gradio authentication file path. The file should contain one or more user:password pairs in the same format as above.', default=None)
group.add_argument('--ssl-keyfile', type=str, help='The path to the SSL certificate key file.', default=None)
group.add_argument('--ssl-certfile', type=str, help='The path to the SSL certificate cert file.', default=None)
group.add_argument('--subpath', type=str, help='Customize the subpath for gradio, use with reverse proxy')
group.add_argument('--old-colors', action='store_true', help='Use the legacy Gradio colors, before the December/2024 update.')
group.add_argument('--portable', action='store_true', help='Hide features not available in portable mode like training.')

# API
group = parser.add_argument_group('API')
group.add_argument('--api', action='store_true', help='Enable the API extension.')
group.add_argument('--public-api', action='store_true', help='Create a public URL for the API using Cloudfare.')
group.add_argument('--public-api-id', type=str, help='Tunnel ID for named Cloudflare Tunnel. Use together with public-api option.', default=None)
group.add_argument('--api-port', type=int, default=5000, help='The listening port for the API.')
group.add_argument('--api-key', type=str, default='', help='API authentication key.')
group.add_argument('--admin-key', type=str, default='', help='API authentication key for admin tasks like loading and unloading models. If not set, will be the same as --api-key.')
group.add_argument('--api-enable-ipv6', action='store_true', help='Enable IPv6 for the API')
group.add_argument('--api-disable-ipv4', action='store_true', help='Disable IPv4 for the API')
group.add_argument('--nowebui', action='store_true', help='Do not launch the Gradio UI. Useful for launching the API in standalone mode.')

# Deprecated parameters
group = parser.add_argument_group('Deprecated')

# Handle CMD_FLAGS.txt
cmd_flags_path = Path(__file__).parent.parent / "user_data" / "CMD_FLAGS.txt"
if cmd_flags_path.exists():
    with cmd_flags_path.open('r', encoding='utf-8') as f:
        cmd_flags = ' '.join(
            line.strip().rstrip('\\').strip()
            for line in f
            if line.strip().rstrip('\\').strip() and not line.strip().startswith('#')
        )

    if cmd_flags:
        # Command-line takes precedence over CMD_FLAGS.txt
        sys.argv = [sys.argv[0]] + shlex.split(cmd_flags) + sys.argv[1:]


args = parser.parse_args()
args_defaults = parser.parse_args([])

# Create a mapping of all argument aliases to their canonical names
alias_to_dest = {}
for action in parser._actions:
    for opt in action.option_strings:
        alias_to_dest[opt.lstrip('-').replace('-', '_')] = action.dest

provided_arguments = []
for arg in sys.argv[1:]:
    arg = arg.lstrip('-').replace('-', '_')
    if arg in alias_to_dest:
        provided_arguments.append(alias_to_dest[arg])
    elif hasattr(args, arg):
        provided_arguments.append(arg)

# Default generation parameters
neutral_samplers = default_preset()

# UI defaults
settings = {
    'show_controls': True,
    'start_with': '',
    'mode': 'instruct',
    'chat_style': 'cai-chat',
    'chat-instruct_command': 'Continue the chat dialogue below. Write a single reply for the character "<|character|>".\n\n<|prompt|>',
    'enable_web_search': False,
    'web_search_pages': 3,
    'prompt-notebook': '',
    'preset': 'Qwen3 - Thinking' if Path('user_data/presets/Qwen3 - Thinking.yaml').exists() else None,
    'max_new_tokens': 512,
    'max_new_tokens_min': 1,
    'max_new_tokens_max': 4096,
    'prompt_lookup_num_tokens': 0,
    'max_tokens_second': 0,
    'auto_max_new_tokens': True,
    'ban_eos_token': False,
    'add_bos_token': True,
    'enable_thinking': True,
    'skip_special_tokens': True,
    'stream': True,
    'static_cache': False,
    'truncation_length': 8192,
    'seed': -1,
    'custom_stopping_strings': '',
    'custom_token_bans': '',
    'negative_prompt': '',
    'dark_theme': True,
    'show_two_notebook_columns': False,
    'paste_to_attachment': False,
    'include_past_attachments': True,

    # Generation parameters - Curve shape
    'temperature': 0.6,
    'dynatemp_low': neutral_samplers['dynatemp_low'],
    'dynatemp_high': neutral_samplers['dynatemp_high'],
    'dynatemp_exponent': neutral_samplers['dynatemp_exponent'],
    'smoothing_factor': neutral_samplers['smoothing_factor'],
    'smoothing_curve': neutral_samplers['smoothing_curve'],

    # Generation parameters - Curve cutoff
    'min_p': neutral_samplers['min_p'],
    'top_p': 0.95,
    'top_k': 20,
    'typical_p': neutral_samplers['typical_p'],
    'xtc_threshold': neutral_samplers['xtc_threshold'],
    'xtc_probability': neutral_samplers['xtc_probability'],
    'epsilon_cutoff': neutral_samplers['epsilon_cutoff'],
    'eta_cutoff': neutral_samplers['eta_cutoff'],
    'tfs': neutral_samplers['tfs'],
    'top_a': neutral_samplers['top_a'],
    'top_n_sigma': neutral_samplers['top_n_sigma'],

    # Generation parameters - Repetition suppression
    'dry_multiplier': neutral_samplers['dry_multiplier'],
    'dry_allowed_length': neutral_samplers['dry_allowed_length'],
    'dry_base': neutral_samplers['dry_base'],
    'repetition_penalty': neutral_samplers['repetition_penalty'],
    'frequency_penalty': neutral_samplers['frequency_penalty'],
    'presence_penalty': neutral_samplers['presence_penalty'],
    'encoder_repetition_penalty': neutral_samplers['encoder_repetition_penalty'],
    'no_repeat_ngram_size': neutral_samplers['no_repeat_ngram_size'],
    'repetition_penalty_range': neutral_samplers['repetition_penalty_range'],

    # Generation parameters - Alternative sampling methods
    'penalty_alpha': neutral_samplers['penalty_alpha'],
    'guidance_scale': neutral_samplers['guidance_scale'],
    'mirostat_mode': neutral_samplers['mirostat_mode'],
    'mirostat_tau': neutral_samplers['mirostat_tau'],
    'mirostat_eta': neutral_samplers['mirostat_eta'],

    # Generation parameters - Other options
    'do_sample': neutral_samplers['do_sample'],
    'dynamic_temperature': neutral_samplers['dynamic_temperature'],
    'temperature_last': neutral_samplers['temperature_last'],
    'sampler_priority': neutral_samplers['sampler_priority'],
    'dry_sequence_breakers': neutral_samplers['dry_sequence_breakers'],
    'grammar_string': '',

    # Character settings
    'character': 'Assistant',
    'name1': 'You',
    'name2': 'AI',
    'user_bio': '',
    'context': 'The following is a conversation with an AI Large Language Model. The AI has been trained to answer questions, provide recommendations, and help with decision making. The AI follows user requests. The AI thinks outside the box.',
    'greeting': 'How can I help you today?',
    'custom_system_message': '',
    'instruction_template_str': "{%- set ns = namespace(found=false) -%}\n{%- for message in messages -%}\n    {%- if message['role'] == 'system' -%}\n        {%- set ns.found = true -%}\n    {%- endif -%}\n{%- endfor -%}\n{%- if not ns.found -%}\n    {{- '' + 'Below is an instruction that describes a task. Write a response that appropriately completes the request.' + '\\n\\n' -}}\n{%- endif %}\n{%- for message in messages %}\n    {%- if message['role'] == 'system' -%}\n        {{- '' + message['content'] + '\\n\\n' -}}\n    {%- else -%}\n        {%- if message['role'] == 'user' -%}\n            {{-'### Instruction:\\n' + message['content'] + '\\n\\n'-}}\n        {%- else -%}\n            {{-'### Response:\\n' + message['content'] + '\\n\\n' -}}\n        {%- endif -%}\n    {%- endif -%}\n{%- endfor -%}\n{%- if add_generation_prompt -%}\n    {{-'### Response:\\n'-}}\n{%- endif -%}",
    'chat_template_str': "{%- for message in messages %}\n    {%- if message['role'] == 'system' -%}\n        {%- if message['content'] -%}\n            {{- message['content'] + '\\n\\n' -}}\n        {%- endif -%}\n        {%- if user_bio -%}\n            {{- user_bio + '\\n\\n' -}}\n        {%- endif -%}\n    {%- else -%}\n        {%- if message['role'] == 'user' -%}\n            {{- name1 + ': ' + message['content'] + '\\n'-}}\n        {%- else -%}\n            {{- name2 + ': ' + message['content'] + '\\n' -}}\n        {%- endif -%}\n    {%- endif -%}\n{%- endfor -%}",

    # Extensions
    'default_extensions': [],
}

default_settings = copy.deepcopy(settings)


def do_cmd_flags_warnings():
    # Security warnings
    if args.trust_remote_code:
        logger.warning('trust_remote_code is enabled. This is dangerous.')
    if 'COLAB_GPU' not in os.environ and not args.nowebui:
        if args.share:
            logger.warning("The gradio \"share link\" feature uses a proprietary executable to create a reverse tunnel. Use it with care.")
        if any((args.listen, args.share)) and not any((args.gradio_auth, args.gradio_auth_path)):
            logger.warning("\nYou are potentially exposing the web UI to the entire internet without any access password.\nYou can create one with the \"--gradio-auth\" flag like this:\n\n--gradio-auth username:password\n\nMake sure to replace username:password with your own.")
            if args.multi_user:
                logger.warning('\nThe multi-user mode is highly experimental and should not be shared publicly.')


def fix_loader_name(name):
    if not name:
        return name

    name = name.lower()
    if name in ['llama.cpp', 'llamacpp', 'llama-cpp', 'llama cpp']:
        return 'llama.cpp'
    elif name in ['transformers', 'huggingface', 'hf', 'hugging_face', 'hugging face']:
        return 'Transformers'
    elif name in ['exllamav2', 'exllama-v2', 'ex_llama-v2', 'exlamav2', 'exlama-v2', 'exllama2', 'exllama-2']:
        return 'ExLlamav2'
    elif name in ['exllamav2-hf', 'exllamav2_hf', 'exllama-v2-hf', 'exllama_v2_hf', 'exllama-v2_hf', 'exllama2-hf', 'exllama2_hf', 'exllama-2-hf', 'exllama_2_hf', 'exllama-2_hf']:
        return 'ExLlamav2_HF'
    elif name in ['exllamav3-hf', 'exllamav3_hf', 'exllama-v3-hf', 'exllama_v3_hf', 'exllama-v3_hf', 'exllama3-hf', 'exllama3_hf', 'exllama-3-hf', 'exllama_3_hf', 'exllama-3_hf']:
        return 'ExLlamav3_HF'
    elif name in ['tensorrt', 'tensorrtllm', 'tensorrt_llm', 'tensorrt-llm', 'tensort', 'tensortllm']:
        return 'TensorRT-LLM'


def add_extension(name, last=False):
    if args.extensions is None:
        args.extensions = [name]
    elif last:
        args.extensions = [x for x in args.extensions if x != name]
        args.extensions.append(name)
    elif name not in args.extensions:
        args.extensions.append(name)


def is_chat():
    return True


def load_user_config():
    '''
    Loads custom model-specific settings
    '''
    if Path(f'{args.model_dir}/config-user.yaml').exists():
        file_content = open(f'{args.model_dir}/config-user.yaml', 'r').read().strip()

        if file_content:
            user_config = yaml.safe_load(file_content)
        else:
            user_config = {}
    else:
        user_config = {}

    return user_config


args.loader = fix_loader_name(args.loader)

# Activate the API extension
if args.api or args.public_api:
    add_extension('openai', last=True)

# Load model-specific settings
p = Path(f'{args.model_dir}/config.yaml')
if p.exists():
    model_config = yaml.safe_load(open(p, 'r').read())
else:
    model_config = {}
del p


# Load custom model-specific settings
user_config = load_user_config()

model_config = OrderedDict(model_config)
user_config = OrderedDict(user_config)
=======
import argparse
from collections import OrderedDict
from pathlib import Path

import yaml

from modules.logging_colors import logger

generation_lock = None
model = None
tokenizer = None
is_seq2seq = False
model_name = "None"
lora_names = []
model_dirty_from_training = False

# Chat variables
stop_everything = False
processing_message = '*Is typing...*'

# UI elements (buttons, sliders, HTML, etc)
gradio = {}

# For keeping the values of UI elements on page reload
persistent_interface_state = {}

input_params = []  # Generation input parameters
reload_inputs = []  # Parameters for reloading the chat interface

# For restarting the interface
need_restart = False

# To prevent the persistent chat history from being loaded when
# a session JSON file is being loaded in chat mode
session_is_loading = False

settings = {
    'dark_theme': True,
    'autoload_model': False,
    'max_new_tokens': 200,
    'max_new_tokens_min': 1,
    'max_new_tokens_max': 4096,
    'auto_max_new_tokens': False,
    'seed': -1,
    'character': 'None',
    'name1': 'You',
    'name2': 'Assistant',
    'context': 'This is a conversation with your Assistant. It is a computer program designed to help you with various tasks such as answering questions, providing recommendations, and helping with decision making. You can ask it anything you want and it will do its best to give you accurate and relevant information.',
    'greeting': '',
    'turn_template': '',
    'custom_stopping_strings': '',
    'stop_at_newline': False,
    'add_bos_token': True,
    'ban_eos_token': False,
    'skip_special_tokens': True,
    'truncation_length': 2048,
    'truncation_length_min': 0,
    'truncation_length_max': 16384,
    'mode': 'chat',
    'start_with': '',
    'chat_style': 'TheEncrypted777',
    'instruction_template': 'None',
    'chat-instruct_command': 'Continue the chat dialogue below. Write a single reply for the character "<|character|>".\n\n<|prompt|>',
    'chat_generation_attempts': 1,
    'chat_generation_attempts_min': 1,
    'chat_generation_attempts_max': 10,
    'default_extensions': [],
    'chat_default_extensions': ['gallery'],
    'preset': 'simple-1',
    'prompt': 'QA',
}


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=54))

# Basic settings
parser.add_argument('--notebook', action='store_true', help='Launch the web UI in notebook mode, where the output is written to the same text box as the input.')
parser.add_argument('--chat', action='store_true', help='Launch the web UI in chat mode with a style similar to the Character.AI website.')
parser.add_argument('--multi-user', action='store_true', help='Multi-user mode. Chat histories are not saved or automatically loaded. WARNING: this is highly experimental.')
parser.add_argument('--character', type=str, help='The name of the character to load in chat mode by default.')
parser.add_argument('--model', type=str, help='Name of the model to load by default.')
parser.add_argument('--lora', type=str, nargs="+", help='The list of LoRAs to load. If you want to load more than one LoRA, write the names separated by spaces.')
parser.add_argument("--model-dir", type=str, default='models/', help="Path to directory with all the models")
parser.add_argument("--lora-dir", type=str, default='loras/', help="Path to directory with all the loras")
parser.add_argument('--model-menu', action='store_true', help='Show a model menu in the terminal when the web UI is first launched.')
parser.add_argument('--no-stream', action='store_true', help='Don\'t stream the text output in real time.')
parser.add_argument('--settings', type=str, help='Load the default interface settings from this yaml file. See settings-template.yaml for an example. If you create a file called settings.yaml, this file will be loaded by default without the need to use the --settings flag.')
parser.add_argument('--extensions', type=str, nargs="+", help='The list of extensions to load. If you want to load more than one extension, write the names separated by spaces.')
parser.add_argument('--verbose', action='store_true', help='Print the prompts to the terminal.')

# Model loader
parser.add_argument('--loader', type=str, help='Choose the model loader manually, otherwise, it will get autodetected. Valid options: transformers, autogptq, gptq-for-llama, exllama, exllama_hf, llamacpp, rwkv')

# Accelerate/transformers
parser.add_argument('--cpu', action='store_true', help='Use the CPU to generate text. Warning: Training on CPU is extremely slow.')
parser.add_argument('--auto-devices', action='store_true', help='Automatically split the model across the available GPU(s) and CPU.')
parser.add_argument('--gpu-memory', type=str, nargs="+", help='Maximum GPU memory in GiB to be allocated per GPU. Example: --gpu-memory 10 for a single GPU, --gpu-memory 10 5 for two GPUs. You can also set values in MiB like --gpu-memory 3500MiB.')
parser.add_argument('--cpu-memory', type=str, help='Maximum CPU memory in GiB to allocate for offloaded weights. Same as above.')
parser.add_argument('--disk', action='store_true', help='If the model is too large for your GPU(s) and CPU combined, send the remaining layers to the disk.')
parser.add_argument('--disk-cache-dir', type=str, default="cache", help='Directory to save the disk cache to. Defaults to "cache".')
parser.add_argument('--load-in-8bit', action='store_true', help='Load the model with 8-bit precision (using bitsandbytes).')
parser.add_argument('--bf16', action='store_true', help='Load the model with bfloat16 precision. Requires NVIDIA Ampere GPU.')
parser.add_argument('--no-cache', action='store_true', help='Set use_cache to False while generating text. This reduces the VRAM usage a bit at a performance cost.')
parser.add_argument('--xformers', action='store_true', help="Use xformer's memory efficient attention. This should increase your tokens/s.")
parser.add_argument('--sdp-attention', action='store_true', help="Use torch 2.0's sdp attention.")
parser.add_argument('--trust-remote-code', action='store_true', help="Set trust_remote_code=True while loading a model. Necessary for ChatGLM and Falcon.")

# Accelerate 4-bit
parser.add_argument('--load-in-4bit', action='store_true', help='Load the model with 4-bit precision (using bitsandbytes).')
parser.add_argument('--compute_dtype', type=str, default="float16", help="compute dtype for 4-bit. Valid options: bfloat16, float16, float32.")
parser.add_argument('--quant_type', type=str, default="nf4", help='quant_type for 4-bit. Valid options: nf4, fp4.')
parser.add_argument('--use_double_quant', action='store_true', help='use_double_quant for 4-bit.')

# llama.cpp
parser.add_argument('--threads', type=int, default=0, help='Number of threads to use.')
parser.add_argument('--n_batch', type=int, default=512, help='Maximum number of prompt tokens to batch together when calling llama_eval.')
parser.add_argument('--no-mmap', action='store_true', help='Prevent mmap from being used.')
parser.add_argument('--low-vram', action='store_true', help='Low VRAM Mode')
parser.add_argument('--mlock', action='store_true', help='Force the system to keep the model in RAM.')
parser.add_argument('--cache-capacity', type=str, help='Maximum cache capacity. Examples: 2000MiB, 2GiB. When provided without units, bytes will be assumed.')
parser.add_argument('--n-gpu-layers', type=int, default=0, help='Number of layers to offload to the GPU.')
parser.add_argument('--n_ctx', type=int, default=2048, help='Size of the prompt context.')
parser.add_argument('--llama_cpp_seed', type=int, default=0, help='Seed for llama-cpp models. Default 0 (random)')
parser.add_argument('--n_gqa', type=int, default=0, help='grouped-query attention. Must be 8 for llama-2 70b.')
parser.add_argument('--rms_norm_eps', type=float, default=0, help='5e-6 is a good value for llama-2 models.')

# GPTQ
parser.add_argument('--wbits', type=int, default=0, help='Load a pre-quantized model with specified precision in bits. 2, 3, 4 and 8 are supported.')
parser.add_argument('--model_type', type=str, help='Model type of pre-quantized model. Currently LLaMA, OPT, and GPT-J are supported.')
parser.add_argument('--groupsize', type=int, default=-1, help='Group size.')
parser.add_argument('--pre_layer', type=int, nargs="+", help='The number of layers to allocate to the GPU. Setting this parameter enables CPU offloading for 4-bit models. For multi-gpu, write the numbers separated by spaces, eg --pre_layer 30 60.')
parser.add_argument('--checkpoint', type=str, help='The path to the quantized checkpoint file. If not specified, it will be automatically detected.')
parser.add_argument('--monkey-patch', action='store_true', help='Apply the monkey patch for using LoRAs with quantized models.')
parser.add_argument('--quant_attn', action='store_true', help='(triton) Enable quant attention.')
parser.add_argument('--warmup_autotune', action='store_true', help='(triton) Enable warmup autotune.')
parser.add_argument('--fused_mlp', action='store_true', help='(triton) Enable fused mlp.')

# AutoGPTQ
parser.add_argument('--gptq-for-llama', action='store_true', help='DEPRECATED')
parser.add_argument('--autogptq', action='store_true', help='DEPRECATED')
parser.add_argument('--triton', action='store_true', help='Use triton.')
parser.add_argument('--no_inject_fused_attention', action='store_true', help='Do not use fused attention (lowers VRAM requirements).')
parser.add_argument('--no_inject_fused_mlp', action='store_true', help='Triton mode only: Do not use fused MLP (lowers VRAM requirements).')
parser.add_argument('--no_use_cuda_fp16', action='store_true', help='This can make models faster on some systems.')
parser.add_argument('--desc_act', action='store_true', help='For models that don\'t have a quantize_config.json, this parameter is used to define whether to set desc_act or not in BaseQuantizeConfig.')

# ExLlama
parser.add_argument('--gpu-split', type=str, help="Comma-separated list of VRAM (in GB) to use per GPU device for model layers, e.g. 20,7,7")
parser.add_argument('--max_seq_len', type=int, default=2048, help="Maximum sequence length.")

# DeepSpeed
parser.add_argument('--deepspeed', action='store_true', help='Enable the use of DeepSpeed ZeRO-3 for inference via the Transformers integration.')
parser.add_argument('--nvme-offload-dir', type=str, help='DeepSpeed: Directory to use for ZeRO-3 NVME offloading.')
parser.add_argument('--local_rank', type=int, default=0, help='DeepSpeed: Optional argument for distributed setups.')

# RWKV
parser.add_argument('--rwkv-strategy', type=str, default=None, help='RWKV: The strategy to use while loading the model. Examples: "cpu fp32", "cuda fp16", "cuda fp16i8".')
parser.add_argument('--rwkv-cuda-on', action='store_true', help='RWKV: Compile the CUDA kernel for better performance.')

# RoPE
parser.add_argument('--compress_pos_emb', type=int, default=1, help="Positional embeddings compression factor. Should typically be set to max_seq_len / 2048.")
parser.add_argument('--alpha_value', type=int, default=1, help="Positional embeddings alpha factor for NTK RoPE scaling. Scaling is not identical to embedding compression. Use either this or compress_pos_emb, not both.")

# Gradio
parser.add_argument('--listen', action='store_true', help='Make the web UI reachable from your local network.')
parser.add_argument('--listen-host', type=str, help='The hostname that the server will use.')
parser.add_argument('--listen-port', type=int, help='The listening port that the server will use.')
parser.add_argument('--share', action='store_true', help='Create a public URL. This is useful for running the web UI on Google Colab or similar.')
parser.add_argument('--auto-launch', action='store_true', default=False, help='Open the web UI in the default browser upon launch.')
parser.add_argument("--gradio-auth", type=str, help='set gradio authentication like "username:password"; or comma-delimit multiple like "u1:p1,u2:p2,u3:p3"', default=None)
parser.add_argument("--gradio-auth-path", type=str, help='Set the gradio authentication file path. The file should contain one or more user:password pairs in this format: "u1:p1,u2:p2,u3:p3"', default=None)
parser.add_argument("--ssl-keyfile", type=str, help='The path to the SSL certificate key file.', default=None)
parser.add_argument("--ssl-certfile", type=str, help='The path to the SSL certificate cert file.', default=None)

# API
parser.add_argument('--api', action='store_true', help='Enable the API extension.')
parser.add_argument('--api-blocking-port', type=int, default=5000, help='The listening port for the blocking API.')
parser.add_argument('--api-streaming-port', type=int, default=5005, help='The listening port for the streaming API.')
parser.add_argument('--public-api', action='store_true', help='Create a public URL for the API using Cloudfare.')

# Multimodal
parser.add_argument('--multimodal-pipeline', type=str, default=None, help='The multimodal pipeline to use. Examples: llava-7b, llava-13b.')

args = parser.parse_args()
args_defaults = parser.parse_args([])

# Deprecation warnings
if args.autogptq:
    logger.warning('--autogptq has been deprecated and will be removed soon. Use --loader autogptq instead.')
    args.loader = 'autogptq'
if args.gptq_for_llama:
    logger.warning('--gptq-for-llama has been deprecated and will be removed soon. Use --loader gptq-for-llama instead.')
    args.loader = 'gptq-for-llama'

# Security warnings
if args.trust_remote_code:
    logger.warning("trust_remote_code is enabled. This is dangerous.")
if args.share:
    logger.warning("The gradio \"share link\" feature uses a proprietary executable to create a reverse tunnel. Use it with care.")
if args.multi_user:
    logger.warning("The multi-user mode is highly experimental. DO NOT EXPOSE IT TO THE INTERNET.")


def fix_loader_name(name):
    name = name.lower()
    if name in ['llamacpp', 'llama.cpp', 'llama-cpp', 'llama cpp']:
        return 'llama.cpp'
    if name in ['llamacpp_hf', 'llama.cpp_hf', 'llama-cpp-hf', 'llamacpp-hf', 'llama.cpp-hf']:
        return 'llamacpp_HF'
    elif name in ['transformers', 'huggingface', 'hf', 'hugging_face', 'hugging face']:
        return 'Transformers'
    elif name in ['autogptq', 'auto-gptq', 'auto_gptq', 'auto gptq']:
        return 'AutoGPTQ'
    elif name in ['gptq-for-llama', 'gptqforllama', 'gptqllama', 'gptq for llama', 'gptq_for_llama']:
        return 'GPTQ-for-LLaMa'
    elif name in ['exllama', 'ex-llama', 'ex_llama', 'exlama']:
        return 'ExLlama'
    elif name in ['exllama-hf', 'exllama_hf', 'exllama hf', 'ex-llama-hf', 'ex_llama_hf']:
        return 'ExLlama_HF'


if args.loader is not None:
    args.loader = fix_loader_name(args.loader)


def add_extension(name):
    if args.extensions is None:
        args.extensions = [name]
    elif 'api' not in args.extensions:
        args.extensions.append(name)


# Activating the API extension
if args.api or args.public_api:
    add_extension('api')

# Activating the multimodal extension
if args.multimodal_pipeline is not None:
    add_extension('multimodal')


def is_chat():
    return args.chat


def get_mode():
    if args.chat:
        return 'chat'
    elif args.notebook:
        return 'notebook'
    else:
        return 'default'


# Loading model-specific settings
with Path(f'{args.model_dir}/config.yaml') as p:
    if p.exists():
        model_config = yaml.safe_load(open(p, 'r').read())
    else:
        model_config = {}

# Applying user-defined model settings
with Path(f'{args.model_dir}/config-user.yaml') as p:
    if p.exists():
        user_config = yaml.safe_load(open(p, 'r').read())
        for k in user_config:
            if k in model_config:
                model_config[k].update(user_config[k])
            else:
                model_config[k] = user_config[k]

model_config = OrderedDict(model_config)
>>>>>>> Stashed changes
