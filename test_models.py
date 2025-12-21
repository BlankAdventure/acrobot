# -*- coding: utf-8 -*-
"""
Created on Sat Dec 20 20:34:42 2025

@author: BlankAdventure
"""


import pytest
from unittest.mock import patch
from models import catch, validate_format, get_acro, GeminiModel, CerebrasModel


def test_catch_returns_value_when_no_exception():
    @catch
    def good_func(x):
        return x * 2
    assert good_func(3) == 6


def test_catch_returns_none_on_exception(capsys):
    @catch
    def bad_func():
        raise ValueError("boom")

    result = bad_func()

    captured = capsys.readouterr()
    assert result is None
    assert "Model error: boom" in captured.out


@pytest.mark.parametrize(
    "word, sentence, expected",
    [
        ("cat", "Cool Awesome Tiger", True),
        ("dog", "Dark Orange Grape", True),
        ("cat", "Cool Awesome", False),  # too short
        ("cat", "cool awesome is tigers", False), # too long        
        ("cat", "Cold Angry Grape", False), # letter/word mismatch
        ("CAT", "cool angry tiger", True), # case-insensitive
    ],
)
def test_validate_format(word, sentence, expected):
    assert validate_format(word, sentence) is expected


@pytest.mark.parametrize("model",[GeminiModel, CerebrasModel])
def test_get_acro_success_first_try_gemini(model):

    with patch.object(model, "generate_response", 
                      return_value="Cool Awesome Tiger") as mock_generate:

        acro, prompt = get_acro(model, word="cat")

    assert acro == "Cool Awesome Tiger"
    assert "cat" in prompt
    mock_generate.assert_called_once()
    

@pytest.mark.parametrize("model",[GeminiModel, CerebrasModel])    
def test_get_acro_retries_until_valid(model):

    responses = [
        None,
        "Still Wrong",
        "Cool Awesome Tiger",
    ]

    with patch.object(model, "generate_response", 
                      side_effect=responses) as mock_generate:

        acro, _ = get_acro(model, word="cat", retries=3)

    assert acro == "Cool Awesome Tiger"
    assert mock_generate.call_count == 3
    

@pytest.mark.parametrize("model",[GeminiModel, CerebrasModel])    
def test_generate_response_exception_handled(capsys, model):
    
    @catch
    def boom(_):
        raise ValueError("API failure")

    with patch.object(model, "generate_response", side_effect=boom):
        result = model.generate_response("test")

    captured = capsys.readouterr()

    assert result is None
    assert "Model error: API failure" in captured.out
    
   