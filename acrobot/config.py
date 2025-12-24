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
    """App config class."""
    max_history: int
    max_calls: int
    max_word_length: int
    throttle_interval: int
    keywords: list[str]


class Model(BaseModel):
    """Testing config class."""
    name: str

class Logging(BaseModel):
    """Testing config class."""
    level: Literal[*logging.getLevelNamesMapping().keys()]

class Config(BaseModel):
    """CLI config class."""
    acrobot: Acrobot
    model: Model
    logging: Logging


def load_yaml_config(path: pathlib.Path) -> Config:
    """Classmethod returns YAML config"""
    try:
        return yaml.safe_load(path.read_text())
    except FileNotFoundError as error:
        message = "Error: yml config file not found."
        raise FileNotFoundError(error, message) from error

path = pathlib.Path(__file__).parent.parent / 'config.yaml'
settings = Config(**load_yaml_config(path))

class AppOnlyFilter(logging.Filter):
    def filter(self, record):
        return record.name.startswith("__main__")

def setup_logging(level=settings.logging.level) -> None:
    logging.getLogger().handlers.clear()
    root = logging.getLogger()

    if root.handlers:
        return

    root.setLevel(level)

    handler = logging.StreamHandler()
    # handler.addFilter(AppOnlyFilter())
    formatter = logging.Formatter(
        "%(levelname)s | %(name)s | %(filename)s | %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("cerebras").setLevel(logging.WARNING)
