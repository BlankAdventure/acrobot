# -*- coding: utf-8 -*-
"""
Created on Sat Jan  3 17:49:58 2026

@author: BlankAdventure
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from acrobot.models import Model, catch
from acrobot.app import Acrobot

class Dummy(Model):    
    def __init__(self, x=0):
        self.x=x
        self.api_call = MagicMock()
    @catch(ValueError,"user_message")
    def generate_response(self, prompt:str):            
        return self.api_call()

@pytest.fixture
def default_config():
    config = {'acrobot': {'telegram_key': 'dummy_key',
                          'max_history': 5,
                          'max_word_length': 12,
                          'throttle_interval': 5,
                          'keywords': ['beer', 'hash']},
              'model': {'retries': 1, 'use_config': 'testconf'},
              'logging': {'level': 'INFO'},
              'testconf': {'provider': 'Dummy'}}
    return config

@pytest.fixture
def dummy_model():
    return Dummy

@pytest.fixture
def dummy_bot(default_config):
   return Acrobot(default_config, start_telegram=False)


@pytest.fixture
def mock_update():
    mock = MagicMock()
    mock.message = MagicMock()
    mock.message.reply_text = AsyncMock()
    return mock


@pytest.fixture
def mock_context():
    mock = MagicMock()
    mock.args = None
    return mock

