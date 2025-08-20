# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 21:39:33 2025

@author: BlankAdventure
"""

import os
import random
import logging
import asyncio
from collections import deque
from collections.abc import Callable, Awaitable
from typing import Deque
from telegram import Update
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = os.environ.get("telegram_bot")
GEMINI_API_KEY = os.environ.get("genai_key")


TEMPERATURE = 1.1
MAX_HISTORY = 6 # length of conversation history
MAX_CALLS = 50 # max allowable calls to the model API
MAX_WORD_LENGTH = 12 # max length of acronym word in characters
THROTTLE_INTERVAL = 7  # seconds

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
generation_config = GenerationConfig(temperature=TEMPERATURE)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotState:
    def __init__(self):
        self.event_queue: Deque[tuple[Callable,Update,any]] = deque()
        self.queue_event: asyncio.Event = asyncio.Event()
        self.history: list[str] = []
        self.call_count: int = 0
        self.keywords: list[str] = []

state = BotState()


async def queue_processor() -> None:
    '''
    Async loop implementing a leaky bucket rate limiter. Acro requests 
    get added to the event queue and processed every THROTTLE_INTERVAL seconds.
    '''
    while True:
        if not state.event_queue:
            state.queue_event.clear()
            await state.queue_event.wait()
        else:
            func, *args = state.event_queue.popleft()
            await func(*args)
            await asyncio.sleep(THROTTLE_INTERVAL)


# === BOT TASKS ===
async def keyword_task(update: Update, word: str) -> None:
    '''
    Form the bot's reply to a keyword hit.
    '''    
    response = await generate_acro(word)
    if update.message and response:
        await update.message.reply_text(f"Did someone say {word}!?\n" + response,do_quote=False)
    elif update.message:
        await update.message.reply_text("Dammit you broke something")    

async def acro_task(update: Update, word: str) -> None:
    '''
    Form the bot's reply to an acronym request.    
    '''    
    response = await generate_acro(word)    
    if update.message and response:
        await update.message.reply_text(response,do_quote=False)
    elif update.message:
        await update.message.reply_text("Dammit you broke something")

async def generate_acro(word: str) -> None|str:
    '''
    Forms the complete acronym prompt and gets the model's response.
    '''
    
    convo = "\n".join(f"{u}: {m}" for u, m in state.history)
    prompt = PROMPT_TEMPLATE.format(convo=convo, word=word)    
    response = await model_response(prompt)    
    return response

async def model_response(prompt: str) -> None|str:
    '''
    Send the model a prompt and get a response.
    '''
    
    text = None
    try:
        response = await asyncio.to_thread(model.generate_content, 
                                           prompt,
                                           generation_config=generation_config)
        text = response.text.strip()
        state.call_count += 1
    except Exception as e:
        logger.error(f"Model error: {e}")
    return text


# === COMMAND HANDLERS ===
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Posts an introduction message to the chat.        
    '''
    if update.message: await update.message.reply_text("Hi, I'm Acrobot. Use /acro WORD to generate an acronym.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Relays info about the state of the bot.        
    '''
    logger.info("Chat History:\n" + "\n".join(f"{u}: {m}" for u, m in state.history))
    logger.info(f"Queue length: {len(state.event_queue)} | API calls: {state.call_count}")
    if update.message: await update.message.reply_text(
        f"Queue length: {len(state.event_queue)} | API calls: {state.call_count}"
    )


async def add_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Manually add new keywords to the trigger list.
    Usage: /add_keyword kw1 kw2 kw3 ...
    '''
    if context.args is None or len(context.args) < 1:
        if update.message: await update.message.reply_text("Usage: /add_keyword kw1 kw2 kw3 ...")
        return
    state.keywords.extend(context.args)
    
    
    
async def add_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Manually add a new message to the chat history.
    Usage: /add_message username add this message!
    '''
    if context.args is None or len(context.args) < 2:
        if update.message: await update.message.reply_text("Usage: /add_message username add this message!")
        return

    username, message = context.args[0], " ".join(context.args[1:])
    state.history.append((username, message))
    state.history = state.history[-MAX_HISTORY:]
    if update.message: await update.message.reply_text("Message added.")

async def handle_message(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Automatically adds new chat messages to the history.
    '''
    if not update.message or not update.message.from_user:
        return
    
    user = update.message.from_user
    sender = user.username or user.first_name or user.last_name or "Unknown"
    message = update.message.text

    state.history.append((sender, message))
    state.history = state.history[-MAX_HISTORY:]
    
    word = next((w for w in state.keywords if w in message), None)    
    if word:
        state.event_queue.append((keyword_task, update, word))
        state.queue_event.set()        

async def handle_acro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Generates a new acronym and posts it in the chat. If no word is specified
    it will pick at random from the last message.
    '''
    
    if state.call_count >= MAX_CALLS:
        if update.message: await update.message.reply_text("No more! You're wasting my precious tokens!")
        return

    word = context.args[0] if context.args else random.choice(
        state.history[-1][1].split()
    )
    word = word[:MAX_WORD_LENGTH]
    state.event_queue.append((acro_task, update, word))
    state.queue_event.set()


def bot_builder() -> Application:
    '''
    Builds the telegram bot object and adds the callback functions.
    '''

    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    loop = asyncio.get_event_loop()
    loop.create_task(queue_processor())

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))    
    app.add_handler(CommandHandler("add_message", add_message))
    app.add_handler(CommandHandler("add_keyword", add_keyword))
    app.add_handler(CommandHandler("acro", handle_acro))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return app


def run_polling() -> None:
    '''
    Runs the bot in polling mode - no need for a server.
    '''
    app = bot_builder()    
    app.run_polling()

if __name__ == "__main__":
    run_polling()
