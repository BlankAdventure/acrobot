"""
Created on Sun Apr 26 23:20:06 2026

@author: BlankAdventure
"""
import os
from unittest import mock
from unittest.mock import patch

import pytest

from acrobot.config import is_url, load_yaml, DEFAULT_PATH


@pytest.mark.parametrize(
    "path, expected",
    [
        ("c://localfolder//myfile.txt",False),
        ("./folder/filed",False),        
        ("www.mysomesite.com/afile.txt",False),
        ("nothing",False),
        ("http://www.mysomesite.com/afile.txt",True),
    ],
)
def test_is_url(path, expected):
    assert is_url(path) is expected


@patch("acrobot.config.load_yaml_local")
def test_file_invocation(mock_call):
    load_yaml()
    mock_call.assert_called_once_with(DEFAULT_PATH)
    
    
@mock.patch.dict(os.environ, {"ACROBOT_CONFIG_YAML": "http://targetsite.com/file.yaml"})    
@patch("acrobot.config.load_yaml_url")
def test_url_invocation(mock_call):
    load_yaml()
    mock_call.assert_called_once_with("http://targetsite.com/file.yaml")


    