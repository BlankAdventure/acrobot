# -*- coding: utf-8 -*-
"""
Created on Sun Dec 21 14:48:23 2025

@author: BlankAdventure
"""
import pathlib
import logging
from pydantic import BaseModel
import yaml
from typing import Literal

class Acrobot(BaseModel):
    """Bot config class."""
    max_history: int = 5
    max_word_length: int = 12
    throttle_interval: int = 5
    keywords: set[str] = {}


class Model(BaseModel):
    """Model config class."""
    name: str
    retries: int = 0

class Logging(BaseModel):
    """Logging config class."""
    level: Literal[*logging.getLevelNamesMapping().keys()] = "INFO"

class Config(BaseModel):
    """CLI config class."""
    acrobot: Acrobot
    model: Model
    logging: Logging


def load_yaml_config(path: pathlib.Path) -> Config:
    """Returns YAML config"""
    try:
        return yaml.safe_load(path.read_text())
    except FileNotFoundError as error:        
        raise FileNotFoundError(error, "Could not load yaml config file.") from error

path = pathlib.Path(__file__).parent.parent / 'config.yaml'
settings = Config(**load_yaml_config(path))

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
