<<<<<<< Updated upstream
from modules import shared
from modules.logging_colors import logger
from modules.LoRA import add_lora_to_model
from modules.models import load_model, unload_model
from modules.models_settings import get_model_metadata, update_model_parameters
from modules.utils import get_available_loras, get_available_models


def get_current_model_info():
    return {
        'model_name': shared.model_name,
        'lora_names': shared.lora_names,
        'loader': shared.args.loader
    }


def list_models():
    return {'model_names': get_available_models()}


def list_models_openai_format():
    """Returns model list in OpenAI API format"""
    model_names = get_available_models()
    return {
        "object": "list",
        "data": [model_info_dict(name) for name in model_names]
    }


def model_info_dict(model_name: str) -> dict:
    return {
        "id": model_name,
        "object": "model",
        "created": 0,
        "owned_by": "user"
    }


def _load_model(data):
    model_name = data["model_name"]
    args = data["args"]
    settings = data["settings"]

    unload_model()
    model_settings = get_model_metadata(model_name)
    update_model_parameters(model_settings)

    # Update shared.args with custom model loading settings
    if args:
        for k in args:
            if hasattr(shared.args, k):
                setattr(shared.args, k, args[k])

    shared.model, shared.tokenizer = load_model(model_name)

    # Update shared.settings with custom generation defaults
    if settings:
        for k in settings:
            if k in shared.settings:
                shared.settings[k] = settings[k]
                if k == 'truncation_length':
                    logger.info(f"TRUNCATION LENGTH (UPDATED): {shared.settings['truncation_length']}")
                elif k == 'instruction_template':
                    logger.info(f"INSTRUCTION TEMPLATE (UPDATED): {shared.settings['instruction_template']}")


def list_loras():
    return {'lora_names': get_available_loras()[1:]}


def load_loras(lora_names):
    add_lora_to_model(lora_names)


def unload_all_loras():
    add_lora_to_model([])
=======
from modules import shared
from modules.utils import get_available_models
from modules.models import load_model, unload_model
from modules.models_settings import (get_model_settings_from_yamls,
                                     update_model_parameters)

from extensions.openai.embeddings import get_embeddings_model_name
from extensions.openai.errors import *


def get_current_model_list() -> list:
    return [shared.model_name]  # The real chat/completions model, maybe "None"


def get_pseudo_model_list() -> list:
    return [  # these are expected by so much, so include some here as a dummy
        'gpt-3.5-turbo',
        'text-embedding-ada-002',
    ]


def load_model(model_name: str) -> dict:
    resp = {
        "id": model_name,
        "object": "engine",
        "owner": "self",
        "ready": True,
    }
    if model_name not in get_pseudo_model_list() + [get_embeddings_model_name()] + get_current_model_list():  # Real model only
        # No args. Maybe it works anyways!
        # TODO: hack some heuristics into args for better results

        shared.model_name = model_name
        unload_model()

        model_settings = get_model_settings_from_yamls(shared.model_name)
        shared.settings.update(model_settings)
        update_model_parameters(model_settings, initial=True)

        if shared.settings['mode'] != 'instruct':
            shared.settings['instruction_template'] = None

        shared.model, shared.tokenizer = load_model(shared.model_name)

        if not shared.model:  # load failed.
            shared.model_name = "None"
            raise OpenAIError(f"Model load failed for: {shared.model_name}")

    return resp


def list_models(is_legacy: bool = False) -> dict:
    # TODO: Lora's?
    all_model_list = get_current_model_list() + [get_embeddings_model_name()] + get_pseudo_model_list() + get_available_models()

    models = {}

    if is_legacy:
        models = [{"id": id, "object": "engine", "owner": "user", "ready": True} for id in all_model_list]
        if not shared.model:
            models[0]['ready'] = False
    else:
        models = [{"id": id, "object": "model", "owned_by": "user", "permission": []} for id in all_model_list]

    resp = {
        "object": "list",
        "data": models,
    }

    return resp


def model_info(model_name: str) -> dict:
    return {
        "id": model_name,
        "object": "model",
        "owned_by": "user",
        "permission": []
    }
>>>>>>> Stashed changes
