# -*- coding: utf-8 -*-
"""
Created on Sun Dec 21 14:48:23 2025

@author: BlankAdventure
"""
import pathlib
import logging
from typing import Dict, Any, Self
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

path = pathlib.Path(__file__).parent / 'config.yaml'

class Acrobot(BaseModel):
    """Bot config class."""
    max_history: int = Field(default=5, ge=0)
    max_word_length: int = Field(default=12, ge=1)
    throttle_interval: int = Field(default=5, ge=0)
    keywords: set[str] = set()
    model_config = ConfigDict(extra='forbid')

class Model(BaseModel):
    """Model config class."""
    use_config: str
    retries: int = Field(default=0, ge=0)
    model_config = ConfigDict(extra='forbid')

class Logging(BaseModel):
    """Logging config class."""
    level: str = "INFO" 
    model_config = ConfigDict(extra='forbid')
    
class Config(BaseModel):
    """CLI config class."""
    acrobot: Acrobot
    model: Model
    logging: Logging    
    
    model_config = ConfigDict(extra='allow')
    __pydantic_extra__: Dict[str,Any]    
    
    @property
    def use_config(self) -> dict[str,Any]:
        return self.__pydantic_extra__[self.model.use_config]            
    
    @model_validator(mode='after')
    def validation(self) -> Self:
        if self.model.use_config not in self.__pydantic_extra__:
            raise KeyError (f"No settings found for {self.model.use_config}!")            
        if "provider" not in self.use_config:
            raise KeyError (f"{self.model.use_config} must include 'provider' parameter!")           
        return self    
    
def load_yaml_config(path: pathlib.Path) -> Config:    
    """Returns YAML config"""    
    try:
        return yaml.safe_load(path.read_text())
    except FileNotFoundError as error:        
        raise FileNotFoundError(error, "Could not load yaml config file.") from error

def get_settings() -> Config:
    settings = Config(**load_yaml_config(path))
    return settings

#level=settings.logging.level
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
