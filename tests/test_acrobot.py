# -*- coding: utf-8 -*-
"""
Created on Fri Sep 19 16:48:10 2025

@author: BlankAdventure
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from acrobot.acrobot.acrobot import Acrobot, match_words, KEYWORDS


def test_match_words_found():
    message = "Let's grab a beer and go!"
    keywords = {"beer", "hash"}
    assert match_words(message, keywords) == ["beer"]

def test_match_words_none():
    message = "Let's grab a soda"
    keywords = {"beer", "hash"}
    assert match_words(message, keywords) == []


def test_add_keywords():
    bot = Acrobot(keywords=["beer"])
    bot._add_keywords(["hash", "drunk"])
    assert "hash" in bot.keywords
    assert "drunk" in bot.keywords
    assert "beer" in bot.keywords

def test_del_keywords():
    bot = Acrobot(keywords=["beer", "hash", "drunk"])
    bot._del_keywords(["beer", "hash"])
    assert "beer" not in bot.keywords
    assert "hash" not in bot.keywords
    assert "drunk" in bot.keywords

def test_update_history():
    bot = Acrobot()
    for i in range(10):
        bot._update_history(f"user{i}", f"message {i}")
    # Should keep only last MAX_HISTORY = 6
    assert len(bot.history) == 6
    assert bot.history[0][0] == "user4"  # user4 to user9 are kept


@pytest.mark.asyncio
async def test_generate_acro_calls_model_response():
    bot = Acrobot()
    bot.history = [("user1", "Let's get drunk"), ("user2", "Totally down")]
    bot.model_response = AsyncMock(return_value="Downright Rambunctious Unicorns Need Kegs")

    result = await bot.generate_acro("drunk")

    #expected_prompt = PROMPT_TEMPLATE.format(
    #    convo="user1: Let's get drunk\nuser2: Totally down", word="drunk"
    #)
    #bot.model_response.assert_awaited_once_with(expected_prompt)
    assert result == "Downright Rambunctious Unicorns Need Kegs"


# @pytest.mark.asyncio
# @patch("acrobot.client.models.generate_content")
# async def test_model_response_success(mock_generate_content):
#     mock_response = MagicMock()
#     mock_response.text = "Downright Rambunctious Unicorns Need Kegs"
#     mock_generate_content.return_value = mock_response

#     bot = Acrobot()
#     prompt = "Generate an acronym for DRUNK"
#     result = await bot.model_response(prompt)

#     assert "Downright Rambunctious Unicorns Need Kegs" == result
#     assert bot.call_count == 1


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

@pytest.mark.asyncio
async def test_command_start_sends_intro(mock_update, mock_context):
    bot = Acrobot()
    await bot.command_start(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once_with(
        "Hi, I'm Acrobot. Use /acro WORD to generate an acronym."
    )

@pytest.mark.asyncio
async def test_add_keywords_command_updates_keywords(mock_update):
    bot = Acrobot()
    context = MagicMock()
    context.args = ["newword", "beer"]
    
    await bot.add_keywords(mock_update, context)
    
    assert "newword" in bot.keywords
    assert "beer" in bot.keywords

@pytest.mark.asyncio
async def test_del_keywords_command_removes_keywords(mock_update):
    bot = Acrobot(keywords=["beer", "hash"])
    context = MagicMock()
    context.args = ["beer"]
    
    await bot.del_keywords(mock_update, context)
    
    assert "beer" not in bot.keywords
    assert "hash" in bot.keywords

@pytest.mark.asyncio
async def test_add_message_command_updates_history(mock_update):
    bot = Acrobot()
    context = MagicMock()
    context.args = ["alice", "Hello", "world"]

    await bot.add_message(mock_update, context)
    
    assert bot.history[-1] == ("alice", "Hello world")
    mock_update.message.reply_text.assert_awaited_once_with("Message added.")

@pytest.mark.asyncio
async def test_handle_message_with_keyword_queues_task(mock_update):
    bot = Acrobot()
    bot.queue_event = AsyncMock()
    bot.history = []

    await bot.handle_message(mock_update, MagicMock())

    # Message should be added to history
    assert bot.history[-1][0] == "testuser"
    assert bot.event_queue  # task should be in queue
    assert callable(bot.event_queue[0][0])  # should be keyword_task
    assert bot.event_queue[0][2] in KEYWORDS  # matched keyword

@pytest.mark.asyncio
async def test_handle_acro_command_queues_task(mock_update):
    bot = Acrobot()
    bot.history = [("testuser", "Some previous message")]
    bot.queue_event = AsyncMock()
    
    context = MagicMock()
    context.args = []

    await bot.handle_acro(mock_update, context)

    assert bot.event_queue
    assert bot.event_queue[0][0] == bot.acro_task


#pip install pytest pytest-asyncio