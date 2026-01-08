# -*- coding: utf-8 -*-
"""
Created on Sat Jan  3 17:49:58 2026

@author: BlankAdventure
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from acrobot.config import Config
from acrobot.models import Model
from acrobot.app import Acrobot

@pytest.fixture
def default_config():
    config = {'acrobot': {'max_history': 5,
                          'max_word_length': 12,
                          'throttle_interval': 5,
                          'keywords': ['beer', 'hash']},
              'model': {'retries': 1, 'use_config': 'testconf'},
              'logging': {'level': 'INFO'},
              'testconf': {'provider': 'Dummy'}}
    return config

@pytest.fixture
def dummy_model():
    class Dummy(Model):
        def __init__(self, x=0):
            self.x=x
        def generate_response(self, prompt:str):            
           ... # not implemented - we patch this method as needed.
    return Dummy


@pytest.fixture
def dummy_bot(dummy_model, default_config):
    return Acrobot( Config(**default_config),start_telegram=False )

@pytest.fixture
def mock_update():
    mock = MagicMock()
    mock.message = MagicMock()
    mock.message.reply_text = AsyncMock()
    mock.message.text = "Let's get drunk"
    mock.message.from_user = MagicMock()
    mock.message.from_user.username = "testuser"
    return mock


@pytest.fixture
def mock_context():
    mock = MagicMock()
    mock.args = []
    return mock

