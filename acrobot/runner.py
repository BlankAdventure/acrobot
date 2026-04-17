# -*- coding: utf-8 -*-
"""
Created on Mon Sep 15 23:05:44 2025

@author: BlankAdventure
"""
import sys
import argparse
import logging

from acrobot import app
from acrobot.config import setup_logging

logger = logging.getLogger(__name__)
setup_logging("INFO")

def single_word(value: str) -> str:
    if " " in value:
        raise argparse.ArgumentTypeError(
            "value must be a single word (no spaces)"
        )
    return value

def cli(word: str, config_name: str) -> None:
    
    from acrobot.config import get_settings
    from acrobot.models import get_acro_safe, build_model
    
    logger.info(f"Testing with '{word}' and {config_name}.")
    settings = get_settings()
    if config_name is None:
        config = settings.use_config        
    else:
        config = getattr(settings, config_name)

    logger.info(f"Using: {config}")
                
    llm = build_model(config)
    print(get_acro_safe(llm, word, retries=0))

def run_webhook(webhook_url: str | None, ip_addr: str, port: int) -> None:
    """
    Run in webhook mode.
    """
    logger.info("Launching in webhook mode.")

    import uvicorn

    bot = app.Acrowebhook(webhook_url=webhook_url)
    uvicorn.run(bot, host=ip_addr, port=port)  # this will block


def run_polling() -> None:
    """
    Run in polling mode.
    """
    logger.info("Launching in polling mode.")
    bot = app.Acrobot()
    bot.start(True)  # this will block


def main(argv=None):
    
    parser = argparse.ArgumentParser(prog="acrobot")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # polling
    subparsers.add_parser("polling", help='Run in polling mode.')
    
    # webhook
    webhook = subparsers.add_parser("webhook", help='Run in webhook mode.')
    
    
    webhook.add_argument("-p", help="server port (listening)", required=True, type=int)
    webhook.add_argument("-a", help="server IP address (listening)", default="0.0.0.0", type=str)
    webhook.add_argument("-w", help="webhook URL", default=None, type=str)    
    
    # word mode
    test = subparsers.add_parser("test", help='Generate an acronym.')
    test.add_argument("word", type=single_word, help='A single word to acronymize')
    test.add_argument("config", nargs="?", help="optional config from config.yaml")    

    args = parser.parse_args(argv)

    if args.command == "webhook":
        run_webhook(args.w, args.a, args.p)
    elif args.command == "polling":
        run_polling()
    elif args.command == "test":
        cli(args.word,args.config)

if __name__ == "__main__":
    main()
    #sys.exit(main())
    #sys.exit(main(sys.argv[1:]))
