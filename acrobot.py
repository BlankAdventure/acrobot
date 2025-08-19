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
MAX_HISTORY = 6  # length of conversation history
MAX_CALLS = 50  # max allowable calls to the model API
MAX_WORD_LENGTH = 12  # max length of acronym word in characters
THROTTLE_INTERVAL = 7  # seconds

SYSTEM_INSTRUCTION = """
You are a pirate in a telegram chat group. You like posting funny, creative, nauticial acronyms inspired by the conversation.

- The acronym words must form a proper sentence.
- THe sentence should relate to the conversation as much as possible.
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
model = genai.GenerativeModel(
    "gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotState:
    def __init__(self):
        self.event_queue: Deque[tuple[Update, str]] = deque()
        self.queue_event: asyncio.Event = asyncio.Event()
        self.history: list = []
        self.call_count: int = 0


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

        if state.event_queue:
            update, prompt = state.event_queue.popleft()
            try:
                response = await asyncio.to_thread(model.generate_content,
                                                   prompt,
                                                   generation_config=generation_config)
                if update.message:
                    await update.message.reply_text(response.text.strip())
            except Exception as e:
                logger.error(f"Model error: {e}")
                if update.message:
                    await update.message.reply_text("Dammit you broke something")
            await asyncio.sleep(THROTTLE_INTERVAL)


# === COMMAND HANDLERS ===
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Posts an introduction message to the chat.
    '''
    if update.message:
        await update.message.reply_text("Hi, I'm Acrobot. Use /acro WORD to generate an acronym.")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Relays info about the state of the bot.
    '''
    logger.info("Chat History:\n" +
                "\n".join(f"{u}: {m}" for u, m in state.history))
    logger.info(
        f"Queue length: {len(state.event_queue)} | API calls: {state.call_count}")
    if update.message:
        await update.message.reply_text(
            f"Queue length: {len(state.event_queue)} | API calls: {state.call_count}"
        )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Manually add a new message to the chat history.
    Usage: /add username add this message!
    '''
    if context.args is None or len(context.args) < 2:
        if update.message:
            await update.message.reply_text("Usage: /add username add this message!")
        return

    username, message = context.args[0], " ".join(context.args[1:])
    state.history.append((username, message))
    state.history = state.history[-MAX_HISTORY:]
    if update.message:
        await update.message.reply_text("Message added.")


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


async def generate_acronym(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Generates a new acronym and posts it in the chat. If no word is specified
    it will pick at random from the last message.
    '''

    if state.call_count >= MAX_CALLS:
        if update.message:
            await update.message.reply_text("No more! You're wasting my precious tokens!")
        return

    word = context.args[0] if context.args else random.choice(
        state.history[-1][1].split()
    )
    word = word[:MAX_WORD_LENGTH]

    convo = "\n".join(f"{u}: {m}" for u, m in state.history)
    prompt = PROMPT_TEMPLATE.format(convo=convo, word=word)

    state.event_queue.append((update, prompt))
    state.queue_event.set()
    state.call_count += 1


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
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("acro", generate_acronym))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message))

    return app


def run_polling() -> None:
    '''
    Runs the bot in polling mode - no need for a server.
    '''
    app = bot_builder()
    app.run_polling()


if __name__ == "__main__":
    run_polling()
