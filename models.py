# -*- coding: utf-8 -*-
"""
Created on Fri Dec 19 14:23:33 2025

@author: BlankAdventure
"""
from abc import ABC, abstractmethod
from collections.abc import Callable
from google import genai
from google.genai import types
from cerebras.cloud.sdk import Cerebras


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
    def wrapper(*args, **kwargs) -> str|None:
        result = None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print(f"Model error: {e}")            
        return result
    return wrapper

class Model(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> str|None:
        pass

class GeminiModel(Model):
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
        
    
def validate_format(word: str, acro_sentence: str) -> bool:
    word_letters = list(word.lower())
    acro_letters = [w[0] for w in acro_sentence.lower().split()]    
    return word_letters == acro_letters


def get_acro(model: Model, word:str, convo:str='', retries:int=0) -> tuple[str|None,str]:
    prompt = PROMPT_TEMPLATE.format(convo=convo, word=word)
    acro = model.generate_response(prompt)
    while retries > 0:
        print (retries)
        if acro and validate_format(word, acro):
                break
        else:
            acro = model.generate_response(prompt)
            retries -= 1 
    return (acro, prompt)

if __name__ == "__main__":    
    
    print(' ***** testing *****')
    llm1 = GeminiModel()    
    llm2 = CerebrasModel()    
    
    print( get_acro(llm1,'hash',retries=1) )
    print( get_acro(llm2,'hash',retries=1) )


