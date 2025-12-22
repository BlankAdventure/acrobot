# -*- coding: utf-8 -*-
"""
Created on Fri Dec 19 14:23:33 2025

@author: BlankAdventure
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from google import genai
from google.genai import types, errors
from cerebras.cloud.sdk import Cerebras, APIError
from httpx import ConnectError


import logging
from log_config import setup_logging
logger = logging.getLogger(__name__)


SYS_INSTRUCTION = """
You are in a hash house harriers chat group. You like sending creative, dirty acronyms inspired by the conversation.

- The acronym words should form a proper sentence.
- The response should relate to the conversation if possible.
- Answer in plain text only. Do not use any special formatting or markdown characters.
"""

PROMPT_TEMPLATE = """
# CONVERSATION:
{convo}

Now generate an acronym for the word: "{word}". Reply with only the acronym.
"""

def catch(func: Callable) -> Callable:
    ''' Decorator function for handling failed model API calls '''
    def wrapper(*args, **kwargs) -> str|None:
        result = None
        try:
            result = func(*args, **kwargs)
        except errors.APIError as e:
            logger.error(f"Gemini error: {e}", exc_info=False)
        except APIError as e:
            logger.error(f"Cerberas error: {e}", exc_info=False)
        except ConnectError as e:
            logger.error(f"Connection error: {e}", exc_info=False)                        
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
        return result
    return wrapper

class Model(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> str|None:
        pass

class GeminiModel(Model):
    ''' Use this class for configuring Gemini models '''
    def __init__(self):
        thinking_config = types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
        func_calling = types.AutomaticFunctionCallingConfig(disable=True)
        self.config = types.GenerateContentConfig(
                system_instruction=SYS_INSTRUCTION,
                temperature=1.1,
                thinking_config=thinking_config,
                automatic_function_calling=func_calling
            )
        self.client = genai.Client()
        
    @catch
    def generate_response(self, prompt: str) -> str|None:
        response = self.client.models.generate_content(model='gemini-2.5-flash',
                                                       contents=prompt,
                                                       config=self.config)
        return response.text.strip()

class CerebrasModel(Model):
    ''' Use this class for configuring Cerebras models '''
    def __init__(self):            
        self.client = Cerebras()
        
    @catch
    def generate_response(self, prompt:str) -> str|None:
        messages=[{"role": "system", "content": SYS_INSTRUCTION},
                  {"role": "user", "content": prompt}]  
        
        completion = self.client.chat.completions.create(messages=messages,
                                                         model="gpt-oss-120b",        
                                                         max_completion_tokens=1024,
                                                         temperature=1,
                                                         top_p=0.6,
                                                         stream=False)
        return completion.choices[0].message.content.strip()
        
    
def validate_format(word: str, expansion: str) -> bool:
    '''
    Checks if the word is a valid acronym for the expansion (word count 
    matches letter count; first letter matches each letter in word)    
    '''
    
    word_letters = word.lower()
    acro_letters = ''.join(w[0] for w in expansion.lower().split())    
    return word_letters == acro_letters


def get_acro(model: Model, word:str, convo:str='', retries:int=0) -> tuple[str|None,str]:
    '''
    Interprets word as an acronym and generates an expansion for it (yes this
    function name is rather backwards).   
    '''
    
    prompt = PROMPT_TEMPLATE.format(convo=convo, word=word)      
    logger.info(f"Requested: {word}")        
    logger.debug(f"PROMPT:\n{prompt}")    
    expansion = model.generate_response(prompt)
    while retries > 0:
        if expansion and validate_format(word, expansion):
            break
        expansion = model.generate_response(prompt)
        retries -= 1 
    logger.info(f"Generated: {expansion}")
    return (expansion, prompt)

if __name__ == "__main__":
    setup_logging()
    logger.info('running standalone')
    
    # do some basic sanity checking
    #llm1 = GeminiModel()    
    llm2 = CerebrasModel()    
    
    #print( get_acro(llm1,'beer',retries=1) )
    print( get_acro(llm2,'beer',retries=1) )


