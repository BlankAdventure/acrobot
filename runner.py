# -*- coding: utf-8 -*-
"""
Created on Mon Sep 15 23:05:44 2025

@author: BlankAdventure
"""
import sys
import argparse
import acrobot

def run_webhook(webhook_url: str|None, ip_addr: str, port: int)->None:
    '''
    Run in webhook mode.
    '''
    import uvicorn    
    bot = acrobot.Acrowebhook(webhook_url=webhook_url)      
    uvicorn.run(bot,host=ip_addr,port=port) # this will block


def run_polling()->None:
    '''
    Run in polling mode.
    '''    
    bot = acrobot.Acrobot()    
    bot.start_polling() # this will block


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='command', help='Available commands')
polling_parser = subparsers.add_parser('polling', help='Run in polling mode')
webhook_parser = subparsers.add_parser('webhook', help='Run in webhook mode')
webhook_parser.add_argument('-p', help='server port (listening)', required=True, type=int)
webhook_parser.add_argument('-a', help='server IP address (listening)', default='0.0.0.0', type=str)
webhook_parser.add_argument('-w', help='webhook URL', default=None,type=str)
args = parser.parse_args()

if (args.command == 'polling' and args.panel == False) or len(sys.argv) < 2 :
    run_polling()
elif args.command == 'webhook' and args.panel == False:
    run_webhook(args.w, args.a, args.p)
else:
    parser.print_help()
    
