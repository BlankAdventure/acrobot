# -*- coding: utf-8 -*-
"""
Created on Mon Sep 15 23:05:44 2025

@author: BlankAdventure
"""

import argparse
import logging

from acrobot import app
from acrobot.config import setup_logging

logger = logging.getLogger(__name__)
setup_logging("INFO")


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


def main():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command")
    webhook_parser = subparser.add_parser("webhook", help="Run in webhook mode.")
    webhook_parser.add_argument(
        "-p", help="server port (listening)", required=True, type=int
    )
    webhook_parser.add_argument(
        "-a", help="server IP address (listening)", default="0.0.0.0", type=str
    )
    webhook_parser.add_argument("-w", help="webhook URL", default=None, type=str)

    args = parser.parse_args()

    if args.command == "webhook":
        run_webhook(args.w, args.a, args.p)
    else:
        run_polling()


if __name__ == "__main__":
    main()
