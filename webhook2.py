# -*- coding: utf-8 -*-
"""
Created on Sat Aug 16 13:45:53 2025

@author: BlankAdventure

Run acrobot in webhook mode. This requires launching a server to handle post
requests sent from telegram to the specified webhook address.

webhook2 -> subclasses from Acrobot and FastAPI to provide 'single' interface

ngrok http 8443 
python webhook2.py -a 0.0.0.0 -p 8443 -w https://3a2892b5f5aa.ngrok-free.app
"""

import os
import acrobot
import uvicorn
import argparse
from telegram import Update
from http import HTTPStatus
from typing import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, APIRouter


class Acrowebhook(acrobot.Acrobot, FastAPI):

    def __init__(self, webhook_url: str|None = None) -> None:     
        
        acrobot.Acrobot.__init__(self)        
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
            await self.app.bot.setWebhook(self.webhook_url)            
        async with self.app: 
            await self.app.start()
            yield
            await self.app.stop()
    
    async def webhook_handler(self, request: Request) -> Response:
        """Processes incoming Telegram updates from the webhook."""        
        json_string = await request.json()
        update = Update.de_json(json_string, self.app.bot)
        await self.app.process_update(update)
        return Response(status_code=HTTPStatus.OK)

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', help='server port (listening)',type=int)
    parser.add_argument('-a', help='server IP address (listening)',type=str)
    parser.add_argument('-w', help='webhook URL', default="0.0.0.0",type=str)
    args = parser.parse_args()    
    webhook_url = args.w or os.getenv('webhook_url') or None
    
    bot = Acrowebhook(webhook_url=webhook_url)    
    uvicorn.run(bot, host=args.a, port=args.p)
    
