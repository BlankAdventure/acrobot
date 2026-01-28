<!-- ABOUT THE PROJECT -->
## About The Project

Acrobot is a telegram bot that participates in your chat groups generating fun, creative acronyms (*technically expansions for acronyms) based on the conversation. It can be triggered on certain keywords or directly via the /acro command (see usage). The acronyms are generated via an LLM with an internally-built prompt. It can be run in polling mode or webhook mode with FastAPI and uvicorn.

### Prerequisites

**Telegram API**
1. You'll need a bot API key from telegram: (https://core.telegram.org/bots/tutorial#getting-ready). 
2. Add a `TELEGRAM_API_KEY` environment variable and assign it the key value obtained above.

**LLM API**
1. Acrobot provides built-in support for gemini-2.5-flash and gpt-oss-120b. To use access them, you'll need an API key from Gemini and/or Cerebras.
2. For Gemini, add a `GEMINI_API_KEY` environment variable and assign it your Gemini API key.
3. For Cerebras, add a `CEREBRAS_API_KEY` environment variable assign it your Cerebras key.

For now, acrobot is only able to access keys via these environment variables. Alternate methods (commmand line, config file) will be added in a future release.

### Installation

1. Clone the repo: `git clone https://github.com/BlankAdventure/acrobot.git`
2. Install locally via pip: `pip install . -e`
3. Or with uv, navigate to `acrobot` and run: `uv sync`

## Running It

Acrobot can run in either polling mode or webhook mode.

**Polling Mode**

In polling mode, the code runs a loop polling the telegram API periodically for new chat updates. It is straightforward to launch, in one of two ways.

1. If installed, simply run the CLI command `acrobot`
2. Otherwise, navigate to `acrobot\acrobot` and run `python -m runner.py`

**Webhook Mode**

In webhhok mode, a running http server is required to handle `POST` requests originating from the telegram server (acrobot will handle launching a uvicorn server instance when this mode is invoked). Telegram must be provided with a *webhook address*, that is, an https url to send chat udpates to. 

1. If installed, run the CLI command `acrobot -a <IP_ADDR> -p <PORT> -w <WEBHOOK_URL>`
2. Otherwise, navigate to `acrobot\acrobot` and run `python -m runner.py -a <IP_ADDR> -p <PORT> -w <WEBHOOK_URL>`

If running locally, ngrok can be used to obtain ah https forwarding url. In this case, you would substitute WEBHOOK_URL for the provided ngrok url, and similarly for the port. IP_ADDR can be set to 0.0.0.0. 

Note that webhook mode is preferred over polling as it only induces network traffic when updates are actually available.

## Usage

*IMPORTANT!* Don't forget to add the bot to your chat - remember you named it back when you obtained your telegram bot API key.

Acronym generation can be triggered in three ways:

1. Detecting a keyword appearing in the chat (this can be configured).
2. If invoked via `@acro`, it will pick a random word from the conversation history.
3. Directly via the command: `/acro word` -> `"wonderful oils require drinking"`

Add or remove keywords:

`/add_keyword keyword1 keyword2 keyword3 ...`

`/del_keyword keyword1 keyword2 keyword3 ...`

Add a fake message to the chat context. This can be fun for secretly steering the bot's responses in a particular direction.

`/add_message username add this message!`

## Settings / Configuration

A number of basic settings can be modified by the user via the `/acrobot/acrobot/config.yaml` file. See the file for details.
