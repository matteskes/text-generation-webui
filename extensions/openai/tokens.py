<<<<<<< Updated upstream
from modules.text_generation import decode, encode


def token_count(prompt):
    tokens = encode(prompt)[0]
    return {
        'length': len(tokens)
    }


def token_encode(input):
    tokens = encode(input)[0]
    if tokens.__class__.__name__ in ['Tensor', 'ndarray']:
        tokens = tokens.tolist()

    return {
        'tokens': tokens,
        'length': len(tokens),
    }


def token_decode(tokens):
    output = decode(tokens)
    return {
        'text': output
    }
=======
from extensions.openai.utils import float_list_to_base64
from modules.text_generation import encode, decode
import numpy as np

def token_count(prompt):
    tokens = encode(prompt)[0]

    return {
        'results': [{
            'tokens': len(tokens)
        }]
    }


def token_encode(input, encoding_format):
    # if isinstance(input, list):
    tokens = encode(input)[0]

    return {
        'results': [{
            'tokens': tokens,
            'length': len(tokens),
        }]
    }


def token_decode(tokens, encoding_format):
    # if isinstance(input, list):
    #    if encoding_format == "base64":
    #         tokens = base64_to_float_list(tokens)
    output = decode(tokens)[0]

    return {
        'results': [{
            'text': output
        }]
    }
>>>>>>> Stashed changes
