# -*- coding: utf-8 -*-
"""
Created on Sun Dec 21 14:48:23 2025

@author: BlankAdventure
"""
import os
import logging
import pathlib
import requests
from typing import Any, Dict, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_PATH = str(pathlib.Path(__file__).parent / "config.yaml")

logger = logging.getLogger(__name__)


def is_url(path_or_url: str) -> bool:
    """ Determines if path_or_url is a local file path or a URL """
    
    if path_or_url.startswith(('http://', 'https://')):
        return True
    return False


class Acrobot(BaseModel):
    """Bot config class."""

    telegram_key: str
    max_history: int = Field(default=5, ge=0)
    max_word_length: int = Field(default=12, ge=1)
    throttle_interval: int = Field(default=5, ge=0)
    keywords: set[str] = set()
    model_config = ConfigDict(extra="forbid")

class Prompt(BaseModel):
    """Bot config class."""

    system: str
    user: str
    model_config = ConfigDict(extra="forbid")


class Model(BaseModel):
    """Model config class."""

    use_config: str
    retries: int = Field(default=0, ge=0)
    model_config = ConfigDict(extra="forbid")


class Logging(BaseModel):
    """Logging config class."""

    level: str = "INFO"
    model_config = ConfigDict(extra="forbid")


class Config(BaseModel):
    """CLI config class."""

    acrobot: Acrobot    
    model: Model
    logging: Logging

    model_config = ConfigDict(extra="allow")
    __pydantic_extra__: Dict[str, Any]

    @property
    def use_config(self) -> dict[str, Any]:
        return self.__pydantic_extra__[self.model.use_config]

    @model_validator(mode="after")
    def validation(self) -> Self:
        if self.model.use_config not in self.__pydantic_extra__:
            raise KeyError(f"No settings found for {self.model.use_config}!")
        if "provider" not in self.use_config:
            raise KeyError(
                f"{self.model.use_config} must include 'provider' parameter!"
            )
        return self


def load_yaml_local(path: str) -> dict:
    """Returns YAML config from a file"""
    return yaml.safe_load(pathlib.Path(path).read_text())



def load_yaml_url(url: str) -> dict:
    """Returns YAML config from a URL"""
    
    response = requests.get(url)
    response.raise_for_status()
    return yaml.safe_load(response.text)


def load_yaml() -> dict:
    path_or_url = os.environ.get('ACROBOT_CONFIG_YAML', DEFAULT_PATH )
    print(path_or_url)
    if is_url(path_or_url):        
        logger.info(f"loading yaml from url: {path_or_url}")        
        yaml_content = load_yaml_url(path_or_url)
    else:
        logger.info(f"loading yaml from file: {path_or_url}")        
        yaml_content = load_yaml_local(path_or_url)
    return yaml_content

def get_settings() -> Config:    
    """ Returns validated configuration settings """
    
    yaml_content = load_yaml()    
    print(yaml_content)
    settings = Config(**yaml_content)       
    return settings

def get_prompt() -> Prompt:
    """"Returns only the prompt portion of the config file"""
    
    all_settings = load_yaml()
    prompt = Prompt(**all_settings['prompt'])
    return prompt

# level=settings.logging.level
def setup_logging(level: str) -> None:
    logging.getLogger().handlers.clear()
    root = logging.getLogger()

    if root.handlers:
        return

    root.setLevel(level)
    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(levelname)s | %(name)s | %(filename)s | %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("cerebras").setLevel(logging.WARNING)

if __name__ == "__main__":
    setup_logging("INFO")
    logger.info("running standalone") 
    print ( get_settings() )