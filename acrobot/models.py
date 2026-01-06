# -*- coding: utf-8 -*-
"""
Created on Fri Dec 19 14:23:33 2025

@author: BlankAdventure
"""


import functools
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import cast, Type
from cerebras.cloud.sdk import APIError, Cerebras
from google import genai
from google.genai import errors, types
from httpx import ConnectError
from dataclasses import dataclass
from typing import Any

from config import setup_logging

logger = logging.getLogger(__name__)

SYS_INSTRUCTION = """
You are in a hash house harriers chat group. You like sending creative, dirty acronyms inspired by the conversation.

- The acronym words should form a proper sentence.
- The response should relate to the conversation if possible.
- Answer in plain text only. Do not use any special formatting or markdown characters.
"""

PROMPT_TEMPLATE = """
# CONVERSATION:
{convo}

Now generate an acronym for the word: "{word}". Reply with only the acronym.
"""


def catch(*exceptions: type[Exception]) -> Callable:
    """Decorator function for handling failed model API calls"""

    exceptions = exceptions + (ConnectError,)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> str | None:
            result = None
            try:
                result = func(*args, **kwargs)
            except exceptions as e:
                logger.error(f"CATCH : {type(e).__name__} : {e}", exc_info=False)
            return result
        return wrapper
    return decorator


class Model(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> str | None:
        pass

@dataclass
class GeminiModel(Model):
    """Use this class for configuring Gemini models"""
    
    thinking_budget: int = 0
    temperature: float = 1.1
    model_name: str = "gemini-2.5-flash"
    
    def __post_init__(self):
        thinking_config = types.ThinkingConfig(
            thinking_budget=self.thinking_budget, include_thoughts=False
        )
        func_calling = types.AutomaticFunctionCallingConfig(disable=True)
        self.config = types.GenerateContentConfig(
            system_instruction=SYS_INSTRUCTION,
            temperature=self.temperature,
            thinking_config=thinking_config,
            automatic_function_calling=func_calling,
        )
        self.client = genai.Client()

    @catch(errors.APIError)
    def generate_response(self, prompt: str) -> str | None:
        response = self.client.models.generate_content(
            model=self.model_name, contents=prompt, config=self.config
        )
        return response.text.strip()

@dataclass
class CerebrasModel(Model):
    """Use this class for configuring Cerebras models"""

    model_name: str = "gpt-oss-120b"
    max_completion_tokens: int = 1024
    temperature: float = 1
    top_p: float = 1

    def __post_init__(self):
        self.client = Cerebras()

    @catch(APIError)
    def generate_response(self, prompt: str) -> str | None:
        messages = [
            {"role": "system", "content": SYS_INSTRUCTION},
            {"role": "user", "content": prompt},
        ]

        completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name, 
            max_completion_tokens=self.max_completion_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=False,
        )
        return completion.choices[0].message.content.strip()


def validate_format(word: str, expansion: str) -> bool:
    """
    Checks if the word is a valid acronym for the expansion (word count
    matches letter count; first letter matches each letter in word)
    """

    word_letters = word.lower()
    acro_letters = "".join(w[0] for w in expansion.lower().split())
    return word_letters == acro_letters


def get_acro(
    model: Model, word: str, convo: str = "", retries: int = 0
) -> tuple[str | None, str]:
    """
    Interprets word as an acronym and generates an expansion for it (yes this
    function name is rather backwards).
    """

    prompt = PROMPT_TEMPLATE.format(convo=convo, word=word)
    logger.info(f"Requested: {word}")
    logger.debug(f"PROMPT:\n{prompt}")
    expansion = model.generate_response(prompt)

    count = retries
    while count > 0:
        if expansion and validate_format(word, expansion):
            break
        expansion = model.generate_response(prompt)
        count -= 1
    logger.info(f"Generated: {expansion} (retries: {retries - count})")
    return (expansion, prompt)

def build_model(config: str|dict[str,Any]) -> Model:
    
    if isinstance(config, str):
        config = {'provider': config}
    
    logger.debug(f"Building model with settings:\n{config}")
    
    try:
        provider = config['provider']
    except KeyError as e:
        err_string = "build_model: config_dict must include 'provider' key with model name."
        e.add_note(err_string)
        logger.critical(err_string)
        raise            
        
    look_up = {x.__name__: x for x in Model.__subclasses__()}
    
    try:
        cls = cast(Type[Model], look_up[provider])
        return cls( **{k: v for k, v in config.items() if k != 'provider'} )
    except KeyError as e:
        err_string = f"get_model: {provider} not found. Valid options are: {', '.join(look_up.keys())}"
        e.add_note(err_string)
        logger.critical(err_string)
        raise
    
if __name__ == "__main__":
    setup_logging("INFO")
    logger.info("running standalone")

    llm = build_model('GeminiModel')
    print ( get_acro(llm, "beer", retries=0) )
    