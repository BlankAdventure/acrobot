"""
Created on Sat Feb 14 01:25:34 2026

@author: BlankAdventure
"""

from unittest.mock import patch
from acrobot.runner import main
import pytest

# Confirm that run_polling is called with polling command
@patch('acrobot.runner.run_polling')
def test_polling(mock_func):
    main(["polling"])
    mock_func.assert_called() 


# Confirm functionality of test command
@patch('acrobot.runner.cli')
def test_cli(mock_func):
    
    # happy path, single word
    main(["test","word"])
    mock_func.assert_called_once_with("word", None)

    # happy path, single word and config option
    mock_func.reset_mock()
    main(["test","word","config_x"])
    mock_func.assert_called_once_with("word", "config_x")

    # Two words fail
    mock_func.reset_mock()
    with pytest.raises(SystemExit):
        main(["test","word1 word2"])
        
# Confirm functionality of webhook command    
@patch('acrobot.runner.run_webhook')
def test_webhook(mock_func):    
    
    # port option required; other values use default
    main(["webhook","-p", "12345"])
    mock_func.assert_called_once_with(None, "0.0.0.0", 12345)

    # port option and address option set
    mock_func.reset_mock()
    main(["webhook","-p", "5555", "-a", "1.2.3.4"])
    mock_func.assert_called_once_with(None, "1.2.3.4", 5555)

    # port option and url option set
    mock_func.reset_mock()
    main(["webhook","-p", "5555", "-w", "a_url"])
    mock_func.assert_called_once_with("a_url", "0.0.0.0", 5555)

    # Failure to include port throws error
    mock_func.reset_mock()
    with pytest.raises(SystemExit):    
        main(["webhook","-w", "a_url","-a", "1.2.3.4"])
        
        
        
