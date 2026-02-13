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
    assert is_valid == True
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
    
    assert is_valid == True
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
        
# This checks that in soft failure mode, a response of None is returned when
# an error condition occurs
# def test_sof_failure(caplog, dummy_model):
#     model = dummy_model()

#     with patch.object(model, "generate_response", 
#                       side_effect=ValueError) as mock_generate:
#         acro,qual = get_acro(model, word="cat", retries=0)
#     assert acro == None
#     assert mock_generate.call_count == 1
#     assert qual == False

#     with patch.object(model, "generate_response",
#                       return_value=3.141) as mock_generate:
#         acro,qual = get_acro(model, word="cat", retries=0)
#     assert acro == None
#     assert mock_generate.call_count == 1
#     assert qual == False

#     with patch.object(model, "generate_response",
#                       return_value="not_acro") as mock_generate:
#         acro,qual = get_acro(model, word="cat", retries=1)
#     assert acro == "not_acro"
#     assert mock_generate.call_count == 2
#     assert qual == False


# In hard fail mode, check that we raise AcroError for (1) LLM failure;
# (2) not a string; (3) quality failure
# def test_hard_failure(caplog, dummy_model):
#     model = dummy_model()
#     with patch.object(model, "generate_response", side_effect=ValueError):
#         with pytest.raises(AcroError):         
#             get_acro(model, word="cat", retries=0, hard_fail=True)
    
#     with patch.object(model, "generate_response", return_value=3.141):
#         with pytest.raises(AcroError):         
#             get_acro(model, word="cat", retries=0, hard_fail=True)

#     with patch.object(model, "generate_response", return_value="not_valid"):
#         with pytest.raises(AcroError):         
#             get_acro(model, word="cat", retries=0, hard_fail=True)


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


    