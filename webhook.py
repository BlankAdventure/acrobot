# -*- coding: utf-8 -*-
"""
Created on Sat Aug 16 13:45:53 2025

@author: BlankAdventure

Run acrobot in webhook mode. This requires launching a server to handle post
requests sent from telegram to the specified webhook address.
"""

import os
import acrobot
import uvicorn
import argparse
from telegram import Update
from http import HTTPStatus
from typing import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response

parser = argparse.ArgumentParser()
parser.add_argument('-p', help='server port (listening)',type=int)
parser.add_argument('-a', help='server IP address (listening)',type=str)
parser.add_argument('-w', help='webhook URL', default=None,type=str)
args = parser.parse_args()
webhook_url = args.w or os.getenv('webhook_url') or None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handles application startup and shutdown events."""
    app.state.bot_app = acrobot.bot_builder()
    if webhook_url: 
        await app.state.bot_app.bot.setWebhook(webhook_url)
    async with app.state.bot_app:
        await app.state.bot_app.start()
        yield
        await app.state.bot_app.stop()    

# Initialize the FastAPI application with the lifespan handler.
app = FastAPI(lifespan=lifespan)

# This is the endpoint that Telegram will hit with updates.
# We're listening for POST requests on the path we defined.
@app.post('/')
async def webhook_handler(request: Request) -> Response:
    """Processes incoming Telegram updates from the webhook."""
    json_string = await request.json()
    update = Update.de_json(json_string, app.state.bot_app.bot)
    await app.state.bot_app.process_update(update)
    return Response(status_code=HTTPStatus.OK)

if __name__ == "__main__":
    uvicorn.run(app, host=args.a, port=args.p)
    
