# -*- coding: utf-8 -*-
"""
Created on Sat Dec 20 20:34:42 2025

@author: BlankAdventure
"""
import pytest
from unittest.mock import patch
from acrobot.models import validate_format, get_acro, build_model, AcroError, catch



@pytest.mark.parametrize(
    "word, sentence, expected",
    [
        ("cat", "Cool Awesome Tiger", True),
        ("dogs", "dark Orange grapes Swallow", True),
        ("cat", "Cool Awesome", False),  # too short
        ("cat", "cool awesome is tigers", False), # too long        
        ("cat", "Cold Angry Grape", False), # letter/word mismatch
        ("CAT", "cool angry tiger", True), # case-insensitive
        ("", None, False), # case-insensitive
        (4, 2, False), # case-insensitive
    ],
)
def test_validate_format(word, sentence, expected):
    assert validate_format(word, sentence) is expected

def test_get_acro_success_first_try(dummy_model):
    model = dummy_model()
    with patch.object(model, "generate_response", 
                      return_value="Cool Awesome Tiger") as mock_generate:

        acro, is_valid = get_acro(model, word="cat")

    assert acro == "Cool Awesome Tiger"    
    assert is_valid
    mock_generate.assert_called_once()

def test_get_acro_retries_until_valid(dummy_model):
    model = dummy_model()
    responses = [
        None,
        3.5,
        "Still Wrong",
        "Cool Awesome Tiger",
    ]

    with patch.object(model, "generate_response", 
                      side_effect=responses) as mock_generate:

        acro, is_valid = get_acro(model, word="cat", retries=6)
    
    assert is_valid
    assert acro == "Cool Awesome Tiger"
    assert mock_generate.call_count == 4   


def test_catch_functionality():

   @catch(ZeroDivisionError, "user_message_1")
   @catch(ValueError, "user_message_2")
   def test_func(e):
       raise e

   # Check specified exception re-raised as AcroError with message
   with pytest.raises(AcroError, match="user_message_1"):
       test_func(ZeroDivisionError)

   # Check specified exception re-raised as AcroError with message
   with pytest.raises(AcroError, match="user_message_2"):
       test_func(ValueError)

   # Confirm non-specified exception re-raised as self
   with pytest.raises(TypeError):
       test_func(TypeError)   
      
def api_call():
    pass


def test_get_acro_throws_errors():
    
    class Fake():
        @catch(ValueError, "user_message")
        def generate_response(self, x):
            return api_call()    
    model = Fake()
    
    
    with patch('test_models.api_call') as b:
    
        # sanity check correct behaviour
        b.return_value = "call all trucks"
        acro, is_valid = get_acro(model, word="cat")
        assert is_valid
        assert acro == "call all trucks"

        # incorrect return type throws TypeError
        b.return_value = 10
        with pytest.raises(TypeError):
            _,_ = get_acro(model, word="cat")

        # decorated error re-raised as AcroError
        b.side_effect = ValueError('naked')
        with pytest.raises(AcroError, match="user_message"):
            _,_ = get_acro(model, word="cat")
        
        # 'other' error bubble up
        b.side_effect = IndexError('naked')
        with pytest.raises(IndexError):
            _,_ = get_acro(model, word="cat")
            
            
    
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


    