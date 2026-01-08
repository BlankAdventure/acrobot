# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 21:39:33 2025

@author: BlankAdventure
"""

import re
import os
import random
import logging
import asyncio
from typing import Iterable
from collections.abc import Callable

from http import HTTPStatus
from typing import AsyncIterator
from contextlib import asynccontextmanager

from acrobot.models import get_acro, build_model
from acrobot.config import get_settings, setup_logging, Config

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
    def __init__(self, settings: Config, start_telegram: bool=True) -> None:
        logger.info(f"Initializing with:\n{settings}")
        self.settings = settings
        self.queue: asyncio.Queue[None|Callable] = asyncio.Queue()
        self.history: list[tuple[str, str]] = []
        self.call_count: int = 0 # not implemented
        self.keywords = settings.acrobot.keywords

        model_config = settings.model.use_config
        
        try:
            llm_config = settings.__pydantic_extra__[model_config]            
        except KeyError as e:
            err_string = f"No configuration for {model_config} found! Exiting."
            e.add_note(err_string)
            logger.critical(err_string)
            raise

        self.llm = build_model( llm_config  )
        
        if start_telegram == True:
            logger.info("configuring telegram app.")
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
        else:
            logger.info("telegram app NOT configured.")

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
            await asyncio.sleep(self.settings.acrobot.throttle_interval)
            self.queue.task_done()


    async def generate_acro(self, word: str) -> None | str:
        """
        Forms the complete acronym prompt and gets the model's response.
        """
        
        convo = "\n".join(f"{u}: {m}" for u, m in self.history)
        response, _ = await asyncio.to_thread(
            get_acro, model=self.llm, word=word, convo=convo, 
            retries=self.settings.model.retries
        )
        return response

    # === BOT TASKS ===
    # The following functions are tasks that arise from command requests and 
    # which get added to the processing queue for execution.

    async def keyword_task(self, update: Update, word: str) -> None:
        """
        Form the bot's reply to a keyword hit.
        """
        
        if update.message:
            response = await self.generate_acro(word) 
            if response:
                await update.message.reply_text(
                    f"{word}? Who said {word}!?\n" + response, do_quote=False
                )
            else:
                await update.message.reply_text("Dammit you broke something")

    async def acro_task(self, update: Update, word: str) -> None:
        """
        Form the bot's reply to an acronym request.
        """
        
        if update.message:
            response = await self.generate_acro(word)
            if response:
                await update.message.reply_text(response, do_quote=False)
            else:
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
        if update.message:
            if context.args is None or len(context.args) < 1:
                await update.message.reply_text("Usage: /add_keyword kw1 kw2 kw3 ...")
            else:
                self._add_keywords(context.args)
                await update.message.reply_text("keywords added.", do_quote=True)
                
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
        if update.message:
            if context.args is None or len(context.args) < 2:
                await update.message.reply_text(
                    "Usage: /add_message username add this message!"
                )
            else:
                username, message = context.args[0], " ".join(context.args[1:])
                self._update_history(username, message)    
                await update.message.reply_text("Message added.",do_quote=True)

    async def command_acro(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Generates a new acronym and posts it in the chat. If no word is specified
        it will pick one at random from the history.
        
        This function removes any non-alphabetic characters.
        """
        if update.message:
            word: str = ''
            if context.args:
                word = context.args[0]
            else:
                flat_history = [word for user, msg in self.history for word in (user, *msg.split())]
                word = random.choice(flat_history) if flat_history else ""
    
            word = "".join(char for char in word if char.isalpha())[:self.settings.acrobot.max_word_length]
    
            if word:            
                await self.queue.put( lambda: self.acro_task(update, word) )
            else:         
                await update.message.reply_text("Not allowed boyo!",do_quote=True)

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
        self.history = self.history[-self.settings.acrobot.max_history:]

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

    async def complete(self, stop) -> None:
        """
        Ends the the queue processor loop and waits for remaining tasks to 
        finish.
        """
        if stop:
            await self.queue.put( None )
        await self.queue.join()
        

            
    
    

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
        self.start(False)
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
    settings = get_settings()
    setup_logging(settings.logging.level)
    logger.info("launching in standalone polling mode")
    bot = Acrobot(settings)
    #bot.start(True)  # this will block
