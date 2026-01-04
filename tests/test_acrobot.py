# -*- coding: utf-8 -*-
"""
Created on Fri Sep 19 16:48:10 2025

@author: BlankAdventure
"""
import sys
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acrobot.acrobot import Acrobot, match_words

def test_match_words_found():
    message = "Let's grab a beer and go!"
    keywords = {"beer", "hash"}
    assert match_words(message, keywords) == ["beer"]

def test_match_words_none():
    message = "Let's grab a soda"
    keywords = {"beer", "hash"}
    assert match_words(message, keywords) == []


def test_add_keywords():
    bot = Acrobot()
    bot._add_keywords(["hash", "drunk"])
    assert "hash" in bot.keywords
    assert "drunk" in bot.keywords
    assert "beer" in bot.keywords

def test_del_keywords():
    bot = Acrobot()
    bot._del_keywords(["beer", "hash"])
    assert "beer" not in bot.keywords
    assert "hash" not in bot.keywords
    assert "drunk" in bot.keywords

@patch('acrobot.acrobot.settings.acrobot.max_history', 5)
def test_update_history():
    bot = Acrobot()
    for i in range(10):
        bot._update_history(f"user_{i}", f"message_{i}")    
    assert len(bot.history) == 5
    assert bot.history[0]  == ("user_5","message_5")  
    assert bot.history[-1] == ("user_9","message_9")



# @pytest.mark.asyncio
# @patch("acrobot.client.models.generate_content", side_effect=Exception("API error"))
# async def test_model_response_failure(mock_generate_content):
#     bot = Acrobot()
#     prompt = "Broken prompt"
#     result = await bot.model_response(prompt)
#     assert result is None
#     assert bot.call_count == 0



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


async def test_command_start_sends_intro(mock_update, mock_context):
    bot = Acrobot()
    await bot.command_start(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once_with(
        "Hi, I'm Acrobot. Use /acro WORD to generate an acronym."
    )


async def test_add_keywords_command_updates_keywords(mock_update):
    bot = Acrobot()
    context = MagicMock()
    context.args = ["newword", "beer"]
    
    await bot.command_add_keywords(mock_update, context)
    
    assert "newword" in bot.keywords
    assert "beer" in bot.keywords

@pytest.mark.asyncio
async def test_del_keywords_command_removes_keywords(mock_update):
    bot = Acrobot(keywords=["beer", "hash"])
    context = MagicMock()
    context.args = ["beer"]
    
    await bot.command_del_keywords(mock_update, context)
    
    assert "beer" not in bot.keywords
    assert "hash" in bot.keywords

@pytest.mark.asyncio
async def test_add_message_command_updates_history(mock_update):
    bot = Acrobot()
    context = MagicMock()
    context.args = ["alice", "Hello", "world"]

    await bot.command_add_message(mock_update, context)
    
    assert bot.history[-1] == ("alice", "Hello world")
    mock_update.message.reply_text.assert_awaited_once_with("Message added.",do_quote=True)

