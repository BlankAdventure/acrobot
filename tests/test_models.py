# -*- coding: utf-8 -*-
"""
Created on Sat Dec 20 20:34:42 2025

@author: BlankAdventure
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acrobot.models import catch, validate_format, get_acro, build_model, Model

@pytest.fixture
def dummy_model():
    class Dummy(Model):
        def __init__(self, x=0):
            self.x=x
        def generate_response(self, prompt:str):
           ... # not implemented - we patch this method as needed.
    return Dummy

def test_catch_returns_value_when_no_exception():
    @catch()
    def good_func(x):
        return x * 2
    assert good_func(3) == 6


def test_catch_returns_none_on_exception(caplog):
    @catch(ValueError)
    def bad_func():
        raise ValueError("boom")
    result = bad_func()
    assert result is None
    assert "boom" in caplog.text

@pytest.mark.parametrize(
    "word, sentence, expected",
    [
        ("cat", "Cool Awesome Tiger", True),
        ("dogs", "dark Orange grapes Swallow", True),
        ("cat", "Cool Awesome", False),  # too short
        ("cat", "cool awesome is tigers", False), # too long        
        ("cat", "Cold Angry Grape", False), # letter/word mismatch
        ("CAT", "cool angry tiger", True), # case-insensitive
    ],
)
def test_validate_format(word, sentence, expected):
    assert validate_format(word, sentence) is expected

def test_get_acro_success_first_try(dummy_model):
    model = dummy_model()
    with patch.object(model, "generate_response", 
                      return_value="Cool Awesome Tiger") as mock_generate:

        acro, prompt = get_acro(model, word="cat")

    assert acro == "Cool Awesome Tiger"
    assert "cat" in prompt
    mock_generate.assert_called_once()

def test_get_acro_retries_until_valid(dummy_model):
    model = dummy_model()
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


def test_generate_response_exception_handled(caplog, dummy_model):
    model = dummy_model()
    @catch(ValueError)
    def boom(_):
        raise ValueError("API failure")

    with patch.object(model, "generate_response", side_effect=boom):
        result = model.generate_response("test")

    assert result is None
    assert "API failure" in caplog.text
    

def test_get_model_success_dict(dummy_model):
    config = {'provider': 'Dummy', 'x': 10}    
    model = build_model(config)    
    assert isinstance(model,dummy_model)
    assert model.x == 10

def test_get_model_success_str(dummy_model):
    model = build_model("Dummy")    
    assert isinstance(model,dummy_model)
    assert model.x == 0 #default value


def test_get_model_fails():  
    with pytest.raises(KeyError): 
        build_model("model_doesnt_exist")


    