# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 21:39:33 2025

@author: BlankAdventure
"""

import os
import random
import logging
import asyncio
from typing import Any
from collections import deque
from collections.abc import Callable
from typing import Deque
from http import HTTPStatus
from typing import AsyncIterator
from contextlib import asynccontextmanager

from google import genai
from google.genai import types
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram import Update
from fastapi import FastAPI, Request, Response, APIRouter


# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = os.environ.get("telegram_bot")
GEMINI_API_KEY = os.environ.get("genai_key")


TEMPERATURE = 1.1
THINKING_TOKENS = 0 # No thinking
MAX_HISTORY = 6 # length of conversation history
MAX_CALLS = 50 # max allowable calls to the model API
MAX_WORD_LENGTH = 12 # max length of acronym word in characters
THROTTLE_INTERVAL = 5  # seconds

SYSTEM_INSTRUCTION = """
You are in a hash house harriers chat group. You like sending creative, dirty acronyms inspired by the conversation.

- The acronym words must form a proper sentence.
- THe sentence should relate to the conversation if possible.
- Use only alphabetic characters.
- Reply with only the sentence.

"""

PROMPT_TEMPLATE = """
# CONVERSATION
{convo}

Now generate an acronym for the word "{word}".
"""

# === SETUP ===
client = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#************************************************************
# ACROBOT (BASE) CLASS
# -----------------------------------------------------------
# Wraps a telegram app with desired chat functionality. 
# Can be run 'standalone' by invoking polling mode.
#************************************************************
class Acrobot:
    def __init__(self) -> None:
        self.event_queue: Deque[tuple[Callable,Update,Any]] = deque()
        self.queue_event: asyncio.Event = asyncio.Event()
        self.history: list[tuple[str,str]] = []
        self.call_count: int = 0
        self.keywords: set[str] = set()

        self.telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()    
        self.telegram_app.add_handler(CommandHandler("start", self.command_start))
        self.telegram_app.add_handler(CommandHandler("info", self.command_info))    
        self.telegram_app.add_handler(CommandHandler("add_message", self.add_message))
        self.telegram_app.add_handler(CommandHandler("add_keywords", self.add_keywords))
        self.telegram_app.add_handler(CommandHandler("del_keywords", self.del_keywords))
        self.telegram_app.add_handler(CommandHandler("acro", self.handle_acro))
        self.telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def queue_processor(self) -> None:
        '''
        Async loop implementing a leaky bucket rate limiter. Acro requests 
        get added to the event queue and processed every THROTTLE_INTERVAL seconds.
        '''
        while True:
            if not self.event_queue:
                self.queue_event.clear()
                await self.queue_event.wait()
            else:
                func, *args = self.event_queue.popleft()
                await func(*args)
                await asyncio.sleep(THROTTLE_INTERVAL)
    
    
    # === BOT TASKS ===
    # These are the tasks arise from command requests and get added to
    # the processing queue for execution.
    
    async def keyword_task(self, update: Update, word: str) -> None:
        '''
        Form the bot's reply to a keyword hit.
        '''    
        response = await self.generate_acro(word)
        if update.message and response:
            await update.message.reply_text(f"{word}? Who said {word}!?\n" + response,do_quote=False)
        elif update.message:
            await update.message.reply_text("Dammit you broke something")    
    
    async def acro_task(self, update: Update, word: str) -> None:
        '''
        Form the bot's reply to an acronym request.    
        '''    
        response = await self.generate_acro(word)    
        if update.message and response:
            await update.message.reply_text(response,do_quote=False)
        elif update.message:
            await update.message.reply_text("Dammit you broke something")
    
    async def generate_acro(self, word: str) -> None|str:
        '''
        Forms the complete acronym prompt and gets the model's response.
        '''
        
        convo = "\n".join(f"{u}: {m}" for u, m in self.history)
        prompt = PROMPT_TEMPLATE.format(convo=convo, word=word)    
        response = await self.model_response(prompt)    
        return response
    
    
    async def model_response(self, prompt: str) -> None|str:
        '''
        Send the model a prompt and get a response.
        '''
        text = None
        config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=TEMPERATURE,
                thinking_config=types.ThinkingConfig(thinking_budget=THINKING_TOKENS, include_thoughts=False),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        try:
            response = await asyncio.to_thread(client.models.generate_content,
                                               model='gemini-2.5-flash',
                                               contents=prompt,
                                               config=config)
            if response.text: text = response.text.strip()
            self.call_count += 1
        except Exception as e:
            logger.error(f"Model error: {e}")
        return text
    
    
    # === COMMAND HANDLERS ===
    # These are the callback functions that get invoked when the associated
    # command is issued in a chat.
    
    async def command_start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Posts an introduction message to the chat.        
        '''
        if update.message: await update.message.reply_text("Hi, I'm Acrobot. Use /acro WORD to generate an acronym.")
    
    async def command_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Relays info about the self of the bot.        
        '''
        logger.info("Chat History:\n" + "\n".join(f"{u}: {m}" for u, m in self.history))
        logger.info(f"Keywords: {self.keywords}\n")
        logger.info(f"Queue length: {len(self.event_queue)} | API calls: {self.call_count}")
        if update.message: await update.message.reply_text(f"Queue length: {len(self.event_queue)} | API calls: {self.call_count} | KW: {self.keywords} | {TEMPERATURE=} | {THINKING_TOKENS=}")
    
    
    async def add_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Manually add new keywords to the trigger list.
        Usage: /add_keyword kw1 kw2 kw3 ...
        '''
        if context.args is None or len(context.args) < 1:
            if update.message: await update.message.reply_text("Usage: /add_keyword kw1 kw2 kw3 ...")
            return
        self._add_keywords(context.args)
        
    def _add_keywords (self, keyword_list:list[str]) -> None:
        '''
        Helper function for adding new keywords. We use a reassignment
        technique rather than in-place assignment in order to trigger a 
        descriptor update.        
        '''
        if keyword_list is not None:
            self.keywords = self.keywords.union(keyword_list)

    async def del_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Remove keywords from the trigger list.
        Usage: /del_keyword kw1 kw2 kw3 ...
        '''
        if context.args is None or len(context.args) < 1:
            if update.message: await update.message.reply_text("Usage: /del_keyword kw1 kw2 kw3 ...")
            return
        self._del_keywords(context.args)
        
    def _del_keywords (self, keyword_list:list[str]) -> None:
        '''
        Helper function for removing keywords. We use a reassignment
        technique rather than in-place assignment in order to trigger a 
        descriptor update.        
        '''

        if keyword_list is not None:
            self.keywords = self.keywords.difference(keyword_list)    
    
    async def add_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Manually add a new message to the chat history.
        Usage: /add_message username add this message!
        '''
        if context.args is None or len(context.args) < 2:
            if update.message: await update.message.reply_text("Usage: /add_message username add this message!")
            return
    
        username, message = context.args[0], " ".join(context.args[1:])
        self._update_history(username, message)
        if update.message: await update.message.reply_text("Message added.")
    
    async def handle_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Automatically adds new chat messages to the history.
        '''
        if not update.message or not update.message.from_user:
            return
        
        user = update.message.from_user
        sender = user.username or user.first_name or user.last_name or "Unknown"
        message = update.message.text
    
        if message:
            self._update_history(sender, message)            
            found = [w for w in self.keywords if w in message]
            if len(found) > 0:
                self.event_queue.append((self.keyword_task, update, random.choice(found)))
                self.queue_event.set()        
    
    def _update_history(self, sender: str, message: str) -> None:
        '''
        Helper function for manually adding a message to the conversation
        history. 
        '''
        self.history = self.history + [(sender, message)]
        self.history = self.history[-MAX_HISTORY:]

    
    async def handle_acro(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Generates a new acronym and posts it in the chat. If no word is specified
        it will pick at random from the last message.
        '''
        
        if self.call_count >= MAX_CALLS:
            if update.message: await update.message.reply_text("No more! You're wasting my precious tokens!")
            return
    
        word = context.args[0] if context.args else random.choice(
            self.history[-1][1].split()
        )
        word = word[:MAX_WORD_LENGTH]

        self.event_queue.append((self.acro_task, update, word))
        self.queue_event.set()

    def start_loop(self) -> None:
        '''
        Checks if an existing asyncio event loop is running, and if not 
        starts one. Then, run the queue_processor in the loop.
        '''
        try:
            self.loop = asyncio.get_running_loop()
            logger.info("using running loop")               
        except:
            self.loop = asyncio.new_event_loop()
            logger.info("using existing loop")
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.queue_processor())

    def start_polling(self) -> None:
        '''
        Run acrobot in polling mode.
        '''
        self.start_loop()
        self.telegram_app.run_polling()


#************************************************************
# WEBHOOK CLASS
# -----------------------------------------------------------
# We subclass from Acrobot and use a FastAPI mixin to add
# the necessary functionality for responding to post requests
# issued from telegram to the webhook URL address.
#************************************************************

class Acrowebhook(Acrobot, FastAPI):
    def __init__(self, webhook_url: str|None = None) -> None:        
        Acrobot.__init__(self)        
        self.webhook_url = webhook_url                
        FastAPI.__init__(self, lifespan=self.lifespan)
        router = APIRouter()
        router.add_api_route("/", self.webhook_handler, methods=["POST"])
        self.include_router(router)
        
    @asynccontextmanager
    async def lifespan(self, _: FastAPI) -> AsyncIterator[None]:
        """Handles application startup and shutdown events."""        
        self.start_loop()
        if self.webhook_url: 
            await self.telegram_app.bot.setWebhook(self.webhook_url)            
        async with self.telegram_app: 
            await self.telegram_app.start()
            yield
            await self.telegram_app.stop()
    
    async def webhook_handler(self, request: Request) -> Response:
        """Processes incoming Telegram updates from the webhook."""        
        json_string = await request.json()
        update = Update.de_json(json_string, self.telegram_app.bot)
        await self.telegram_app.process_update(update)
        return Response(status_code=HTTPStatus.OK)


        

