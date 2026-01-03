# -*- coding: utf-8 -*-
"""
Created on Sun Dec 21 14:48:23 2025

@author: BlankAdventure
"""
import pathlib
import logging
from pydantic import BaseModel, ConfigDict, Field
import yaml
from typing import Literal

class Acrobot(BaseModel):
    """Bot config class."""
    max_history: int = Field(default=5, ge=0)
    max_word_length: int = Field(default=12, ge=1)
    throttle_interval: int = Field(default=5, ge=0)
    keywords: set[str] = {}


class Model(BaseModel):
    """Model config class."""
    name: str
    retries: int = Field(default=0, ge=0)

class Logging(BaseModel):
    """Logging config class."""
    level: Literal[*logging.getLevelNamesMapping().keys()] = "INFO"

class Config(BaseModel):
    """CLI config class."""
    acrobot: Acrobot
    model: Model
    logging: Logging
    model_config = ConfigDict(extra='allow')

def load_yaml_config(path: pathlib.Path) -> Config:
    """Returns YAML config"""
    try:
        return yaml.safe_load(path.read_text())
    except FileNotFoundError as error:        
        raise FileNotFoundError(error, "Could not load yaml config file.") from error

path = pathlib.Path(__file__).parent.parent / 'config.yaml'
settings = Config(**load_yaml_config(path),extra="allow")

def setup_logging(level=settings.logging.level) -> None:
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
