# -*- coding: utf-8 -*-
"""
Created on Fri Dec 19 14:23:33 2025

@author: BlankAdventure
"""

import functools
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from typing import Any, Literal, Optional, Type, cast

from cerebras.cloud.sdk import APIConnectionError, Cerebras, RateLimitError
from google import genai
from google.genai import errors, types
from httpx import ConnectError

from acrobot.config import setup_logging

logger = logging.getLogger(__name__)

SYS_INSTRUCTION = """
You are in a hash house harriers chat group. You like sending creative, dirty acronyms inspired by the conversation.

- The acronym words should form a proper sentence.
- The response should relate to the conversation if possible.
- Answer in plain text only. Do not use any special formatting or markdown characters.

"""


PROMPT_TEMPLATE = """
### CONVERSATION ###
{convo}

Now generate an acronym for the word: "{word}". Reply with only the acronym.
"""


class AcroError(Exception):
    """Exception raised for specific application errors."""

    def __init__(self, message: str):
        super().__init__(message)

    def __call__(self) -> str:
        return self.__str__()


def catch(exception: type[Exception], message: str) -> Callable:
    """Decorator function for handling failed model API calls"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> str | None:
            result = None
            try:
                result = func(*args, **kwargs)
            except exception as e:
                logger.error(f"Raising AcroError <{type(e).__name__} : {e}>",exc_info=False)                
                raise AcroError(message) from e
            return result

        return wrapper

    return decorator


class Model(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> Optional[str]:
        pass


@dataclass
class GeminiModel(Model):
    """Use this class for configuring Gemini models"""

    thinking_budget: int = 0
    temperature: float = 1.1
    top_p: float = 0.95
    model_name: str = "gemini-2.5-flash"
    api_key: str | None = None

    def __post_init__(self):
        thinking_config = types.ThinkingConfig(
            thinking_budget=self.thinking_budget, include_thoughts=False
        )
        func_calling = types.AutomaticFunctionCallingConfig(disable=True)
        self.config = types.GenerateContentConfig(
            system_instruction=SYS_INSTRUCTION,
            temperature=self.temperature,
            top_p=self.top_p,
            thinking_config=thinking_config,
            automatic_function_calling=func_calling,
        )
        self.client = genai.Client(api_key=self.api_key)

    @catch(ConnectError, "your internet is busted.")
    @catch(errors.APIError, "dammit, you broke something!")
    def generate_response(self, prompt: str) -> str | None:
        response = self.client.models.generate_content(
            model=self.model_name, contents=prompt, config=self.config
        )
        return response.text.strip()


@dataclass
class CerebrasModel(Model):
    """Use this class for configuring Cerebras models"""

    model_name: str = "gpt-oss-120b"
    max_completion_tokens: int = 2048
    temperature: float = 1
    top_p: float = 1
    api_key: str | None = None
    reasoning_effort: Literal["low", "medium", "high"] = "low"

    def __post_init__(self):
        self.client = Cerebras(api_key=self.api_key)

    @catch(RateLimitError, "slow down there buddy.")
    @catch(APIConnectionError, "your internet is busted.")
    @catch(ConnectError, "your internet is busted.")
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
            reasoning_effort=self.reasoning_effort,
            stream=False,
        )
        return completion.choices[0].message.content.strip()


def validate_format(word: str, expansion: str | None) -> bool:
    """
    Checks if the word is a valid acronym for the expansion (word count
    matches letter count; first letter matches each letter in word)
    """
    if isinstance(word, str) and isinstance(expansion, str):
        word_letters = word.lower()
        acro_letters = "".join(w[0] for w in expansion.lower().split())
        return word_letters == acro_letters
    return False


def build_prompt(word: str, convo: str = "") -> str:
    """
    Helper function for assembling the complete prompt. Provided as a 
    separate function for testing purposes.
    """
    return PROMPT_TEMPLATE.format(convo=convo, word=word)


def get_acro_safe(
    model: Model, word: str, convo: str = "", retries: int = 0
) -> tuple[str|None, bool]:
    
    response: str|None = None
    is_valid: bool = False

    try:
        response, is_valid = get_acro(model, word, convo, retries)
    except AcroError as e:        
        logger.error(f"CAUGHT: {type(e).__name__}", exc_info=False)
        response = e()
        is_valid = False
    except TypeError:
        logger.error("CAUGHT: LLM response must be a string.", exc_info=False)
        response = None
        is_valid = False
    except Exception as e:
        logger.error(f"CAUGHT: {e}", exc_info=True)
        response = None
        is_valid = False        

    return response, is_valid
        




def get_acro(
    model: Model, word: str, convo: str = "", retries: int = 0
) -> tuple[str, bool]:
    """
    Interprets word as an acronym and generates an expansion for it (yes this
    function name is rather backwards).
    """

    is_valid_acro: bool = False

    prompt = build_prompt(convo=convo, word=word)
    logger.info(f"Requested: '{word}'")
    logger.debug(f"PROMPT:\n{prompt}")

    count = retries
    while count >= 0:
        expansion = model.generate_response(prompt)
        is_valid_acro = validate_format(word, expansion)
        count -= 1
        if is_valid_acro:
            break
        sleep(1)

    if not isinstance(expansion, str):
        raise TypeError("LLM response must be a string.")

    logger.info(
        f"Generated: '{expansion}' (retries: {retries - count - 1}, valid: {is_valid_acro})"
    )

    return (expansion, is_valid_acro)


def build_model(config: str | dict[str, Any]) -> Model:

    if isinstance(config, str):
        config = {"provider": config}

    logger.debug(f"Building model with settings:\n{config}")

    try:
        provider = config["provider"]
    except KeyError as e:
        err_string = (
            "build_model: config_dict must include 'provider' key with model name."
        )
        e.add_note(err_string)
        logger.critical(err_string)
        raise

    look_up = {x.__name__: x for x in Model.__subclasses__()}

    try:
        cls = cast(Type[Model], look_up[provider])
        return cls(**{k: v for k, v in config.items() if k != "provider"})
    except KeyError as e:
        err_string = f"get_model: {provider} not found. Valid options are: {', '.join(look_up.keys())}"
        e.add_note(err_string)
        logger.critical(err_string)
        raise


if __name__ == "__main__":
    setup_logging("INFO")
    logger.info("running standalone")

    llm = build_model("GeminiModel")
    print(get_acro_safe(llm, "beer", retries=0))
