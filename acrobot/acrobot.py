# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 21:39:33 2025

@author: BlankAdventure
"""

import re
import os
import sys
import random
import logging
import asyncio
from pathlib import Path
from typing import Iterable
from collections.abc import Callable

from http import HTTPStatus
from typing import AsyncIterator
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent))
from models import get_acro, get_model
from config import settings, setup_logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram import Update
from fastapi import FastAPI, Request, Response, APIRouter

logger = logging.getLogger(__name__)
TELEGRAM_BOT_TOKEN = os.environ.get("telegram_bot")
llm = get_model(settings.model.name)


def match_words(message: str, keywords: Iterable[str]) -> list[str]:
    """
    Returns a list of keywords found in message, if any.
    """
    words = re.split(r"\W+", message.lower())
    found = [w.lower() for w in keywords if w.lower() in words]
    return found


# ************************************************************
# ACROBOT (BASE) CLASS
# -----------------------------------------------------------
# Wraps a telegram app with desired chat functionality.
# Can be run 'standalone' by invoking polling mode.
# ************************************************************
class Acrobot:
    def __init__(self, keywords: list[str] | None = None) -> None:
        self.queue: asyncio.Queue[Callable] = asyncio.Queue()
        self.history: list[tuple[str, str]] = []
        self.call_count: int = 0 # not implemented
        self.keywords = set(keywords) if isinstance(keywords, list) else settings.acrobot.keywords

        self.telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        self.telegram_app.add_handler(CommandHandler("start", self.command_start))
        self.telegram_app.add_handler(CommandHandler("info", self.command_info))
        self.telegram_app.add_handler(CommandHandler("add_message", self.command_add_message))
        self.telegram_app.add_handler(CommandHandler("add_keywords", self.command_add_keywords))
        self.telegram_app.add_handler(CommandHandler("del_keywords", self.command_del_keywords))
        self.telegram_app.add_handler(CommandHandler("acro", self.command_acro))
        self.telegram_app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )


    async def queue_processor(self) -> None:        
        """
        Async loop implementing a leaky bucket rate limiter. Acro requests
        get added to the event queue and processed every THROTTLE_INTERVAL seconds.
        """

        logger.info('queue processor started.')        
        
        while True:
            logger.debug('queue processor awaiting.')
            item = await self.queue.get() 
            logger.debug(f'task received: {item}')
            if item is None: 
                self.queue.task_done()
                logger.info ("loop stopping")
                break            
            await item()            
            await asyncio.sleep(settings.acrobot.throttle_interval)
            self.queue.task_done()


    async def generate_acro(self, word: str) -> None | str:
        """
        Forms the complete acronym prompt and gets the model's response.
        """
        
        convo = "\n".join(f"{u}: {m}" for u, m in self.history)
        response, _ = await asyncio.to_thread(
            get_acro, model=llm, word=word, convo=convo, 
            retries=settings.model.retries
        )
        return response

    # === BOT TASKS ===
    # The following functions are tasks that arise from command requests and 
    # which get added to the processing queue for execution.

    async def keyword_task(self, update: Update, word: str) -> None:
        """
        Form the bot's reply to a keyword hit.
        """
        response = await self.generate_acro(word)
        if update.message and response:
            await update.message.reply_text(
                f"{word}? Who said {word}!?\n" + response, do_quote=False
            )
        elif update.message:
            await update.message.reply_text("Dammit you broke something")

    async def acro_task(self, update: Update, word: str) -> None:
        """
        Form the bot's reply to an acronym request.
        """
        response = await self.generate_acro(word)
        
        if update.message and response:
            await update.message.reply_text(response, do_quote=False)
        elif update.message:
            await update.message.reply_text("Dammit you broke something")


    # === COMMAND HANDLERS ===
    # These are the callback functions that get invoked when the associated
    # command is issued in a chat.

    async def command_start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Posts an introduction message to the chat.
        """
        if update.message:
            await update.message.reply_text(
                "Hi, I'm Acrobot. Use /acro WORD to generate an acronym."
            )

    async def command_info(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Relays info about the self of the bot.
        """
        #logger.info("Chat History:\n" + "\n".join(f"{u}: {m}" for u, m in self.history))
        #logger.info(f"Keywords: {self.keywords}\n")
        #logger.info(
        #    f"Queue length: {len(self.event_queue)} | API calls: {self.call_count}"
        #)
        if update.message:
            await update.message.reply_text("INFO INFO INFO!")
                #f"Queue length: {len(self.queue)} | API calls: {self.call_count} | KW: {self.keywords} "
            

    async def command_add_keywords(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Manually add new keywords to the trigger list.
        Usage: /add_keyword kw1 kw2 kw3 ...
        """
        if context.args is None or len(context.args) < 1:
            if update.message:
                await update.message.reply_text("Usage: /add_keyword kw1 kw2 kw3 ...")
            return
        self._add_keywords(context.args)

    def _add_keywords(self, keyword_list: list[str]) -> None:
        """
        Helper function for adding new keywords. We use a reassignment
        technique rather than in-place assignment in order to trigger a
        descriptor update.
        """
        if keyword_list is not None:
            self.keywords = self.keywords.union(keyword_list)

    async def command_del_keywords(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Remove keywords from the trigger list.
        Usage: /del_keyword kw1 kw2 kw3 ...
        """
        if context.args is None or len(context.args) < 1:
            if update.message:
                await update.message.reply_text("Usage: /del_keyword kw1 kw2 kw3 ...")
            return
        self._del_keywords(context.args)

    def _del_keywords(self, keyword_list: list[str]) -> None:
        """
        Helper function for removing keywords. We use a reassignment
        technique rather than in-place assignment in order to trigger a
        descriptor update.
        """

        if keyword_list is not None:
            self.keywords = self.keywords.difference(keyword_list)

    async def command_add_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Manually add a new message to the chat history.
        Usage: /add_message username add this message!
        """
        if context.args is None or len(context.args) < 2:
            if update.message:
                await update.message.reply_text(
                    "Usage: /add_message username add this message!"
                )
            return

        username, message = context.args[0], " ".join(context.args[1:])
        self._update_history(username, message)
        if update.message:
            await update.message.reply_text("Message added.")

    async def command_acro(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Generates a new acronym and posts it in the chat. If no word is specified
        it will pick at random from the last message.
        """
        word = (
            context.args[0]
            if context.args
            else random.choice(self.history[-1][1].split())
        )
        word = word[:settings.acrobot.max_word_length]
        logger.info(f"command_acro: {word}")
        await self.queue.put( lambda: self.acro_task(update, word) )
        

    # === MESSAGE HANDLER ===
    # General-purpose chat message handler. 

    async def handle_message(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Automatically adds new chat messages to the history.
        """
        if not update.message or not update.message.from_user:
            return

        user = update.message.from_user
        sender = user.username or user.first_name or user.last_name or "Unknown"
        message = update.message.text

        if message:
            self._update_history(sender, message)
            found = match_words(message, self.keywords)
            if len(found) > 0:
                await self.queue.put( lambda: self.keyword_task(update, random.choice(found)) )

    def _update_history(self, sender: str, message: str) -> None:
        """
        Helper function for manually adding a message to the conversation
        history.
        """        
        self.history.append((sender, message))
        self.history = self.history[-settings.acrobot.max_history:]

    def start(self, run_polling: bool = False) -> None:
        async def go() -> None:
            self.task_qp = asyncio.create_task(self.queue_processor())  
        
        try:
            loop = asyncio.get_event_loop()
            logger.debug ('using existing event loop')            
        except RuntimeError:
            loop = asyncio.new_event_loop()
            logger.debug ('got new event loop')
        
        asyncio.set_event_loop(loop)             
        self.task_go = loop.create_task(go())
        
        if run_polling:
            self.telegram_app.run_polling()

    async def shutdown(self) -> None:
        """
        Ends the the queue processor loop and waits for remaining tasks to 
        finish.
        """
        await self.queue.put( None )
        await asyncio.wait_for(self.task_go,timeout=60)
        await asyncio.wait_for(self.task_qp,timeout=60)
        
        
    
    

# ************************************************************
# WEBHOOK CLASS
# -----------------------------------------------------------
# We subclass from Acrobot and use a FastAPI mixin to add
# the necessary functionality for responding to post requests
# issued from telegram to the webhook URL address.
# ************************************************************


class Acrowebhook(Acrobot, FastAPI):
    def __init__(
        self, webhook_url: str | None = None, keywords: list[str] | None = None
    ) -> None:
        Acrobot.__init__(self, keywords)
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


if __name__ == "__main__":
    setup_logging()
    logger.info("launching in standalone polling mode")
    bot = Acrobot()
    bot.start(True)  # this will block
