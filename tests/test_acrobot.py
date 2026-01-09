# -*- coding: utf-8 -*-
"""
Created on Fri Sep 19 16:48:10 2025

@author: BlankAdventure
"""
import time
import pytest
from unittest.mock import MagicMock, patch, call
from acrobot.app import match_words, Acrobot

def test_match_words_found():
    message = "Let's grab a beer and go!"
    keywords = {"beer", "hash"}
    assert match_words(message, keywords) == ["beer"]

def test_match_words_none():
    message = "Let's grab a soda"
    keywords = {"beer", "hash"}
    assert match_words(message, keywords) == []

# note: "beer", "hash" added by default
def test_add_keywords(dummy_bot):    
    dummy_bot._add_keywords(["hash", "drunk", "sister"])
    assert "beer" in dummy_bot.keywords
    assert "hash" in dummy_bot.keywords
    assert "drunk" in dummy_bot.keywords
    assert "sister" in dummy_bot.keywords
    assert len(dummy_bot.keywords) == 4

# note: "beer", "hash" added by default
def test_del_keywords(dummy_bot):    
    dummy_bot._del_keywords(["beer", "sister"])
    assert "beer" not in dummy_bot.keywords    
    assert "hash" in dummy_bot.keywords


def test_update_history(dummy_bot):    
    for i in range(10):
        dummy_bot._update_history(f"user_{i}", f"message_{i}")    
    assert len(dummy_bot.history) == 5
    assert dummy_bot.history[0]  == ("user_5","message_5")  
    assert dummy_bot.history[-1] == ("user_9","message_9")


async def test_command_start_sends_intro(dummy_bot, mock_update, mock_context):
    await dummy_bot.command_start(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once_with(
        "Hi, I'm Acrobot. Use /acro WORD to generate an acronym."
    )


async def test_add_keywords_command_updates_keywords(dummy_bot, mock_update):
    context = MagicMock()
    context.args = ["newword1", "newword2"]    
    await dummy_bot.command_add_keywords(mock_update, context)    
    assert "newword1" in dummy_bot.keywords
    assert "newword2" in dummy_bot.keywords
    mock_update.message.reply_text.assert_awaited_once_with(
        "keywords added.",do_quote=True
    )


async def test_del_keywords_command_removes_keywords(dummy_bot, mock_update):
    context = MagicMock()
    context.args = ["beer","nonexistant"]    
    await dummy_bot.command_del_keywords(mock_update, context)    
    assert "beer" not in dummy_bot.keywords
    assert "hash" in dummy_bot.keywords

async def test_add_message_command_updates_history(dummy_bot, mock_update):
    context = MagicMock()
    context.args = ["Alice", "hello", "world"]
    await dummy_bot.command_add_message(mock_update, context)    
    assert dummy_bot.history[-1] == ("Alice", "hello world")
    mock_update.message.reply_text.assert_awaited_once_with("Message added.",do_quote=True)
    
async def test_command_acro_soft_fail(default_config, mock_update, mock_context):
    
    default_config['acrobot']['throttle_interval'] = 1
    default_config['model']['retries'] = 1
    
    bot = Acrobot(default_config, start_telegram=False)    
    
    with patch.object(bot.llm, 'generate_response') as mock_func:

        mock_func.configure_mock(return_value = "call on weeds")    
        mock_context.args = ["cow"]    
        
        bot.start(run_polling=False) #start bot without polling    
        await bot.command_acro(mock_update, mock_context)            
        await bot.complete(stop=False)
        mock_update.message.reply_text.assert_awaited_once_with('call on weeds', do_quote=False)

        mock_func.configure_mock(return_value = "invalid acronym") 
        await bot.command_acro(mock_update, mock_context)            
        await bot.complete(stop=False)
        mock_update.message.reply_text.assert_awaited_with("invalid acronym", do_quote=False)

        mock_func.configure_mock(side_effect=ValueError) 
        await bot.command_acro(mock_update, mock_context)            
        await bot.complete(stop=True)
        mock_update.message.reply_text.assert_awaited_with('Dammit you broke something', do_quote=True)

        assert len(mock_func.mock_calls) == 5
        assert len(mock_update.message.reply_text.mock_calls) == 3


async def test_command_acro_timing(default_config, mock_update, mock_context):
    
    default_config['acrobot']['throttle_interval'] = 2
    default_config['model']['retries'] = 0
    
    bot = Acrobot(default_config, start_telegram=False)    
    
    with patch.object(bot.llm, 'generate_response') as mock_func:

        mock_func.configure_mock(return_value = "call on weeds")    
        mock_context.args = ["cow"]    
        
        bot.start(run_polling=False) 
        
        start_time = time.perf_counter()
        
        await bot.command_acro(mock_update, mock_context)           
        await bot.command_info(mock_update, mock_context)     

        mock_context.args = ["dog"]    
        await bot.command_acro(mock_update, mock_context)            
        await bot.complete(stop=True)
        
        duration = time.perf_counter() - start_time        
    
    expected = [call('INFO INFO INFO!'),
                call('call on weeds', do_quote=False),
                call('call on weeds', do_quote=False)]

    assert mock_update.message.reply_text.mock_calls == expected
    assert duration == pytest.approx(4.25, abs=0.15)        
    