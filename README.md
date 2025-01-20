# Financial Market Telegram Bot

A Telegram bot that allows users to select financial assets and timeframes for market analysis.

## Features

- Select from various financial assets (Gold, Bitcoin, USD Index, Crude Oil, Nasdaq)
- Choose different timeframes (1min to 1day)
- Interactive inline keyboard buttons
- User-friendly interface

## Setup Instructions

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Get a Telegram Bot Token:
   - Talk to [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot using the `/newbot` command
   - Copy the API token provided

3. Configure the bot:
   - Open `bot.py`
   - Replace `'YOUR_BOT_TOKEN_HERE'` with your actual bot token

4. Run the bot:
```bash
python bot.py
```

## Usage

1. Start the bot with `/start` command
2. Select an asset using the provided buttons
3. Choose a timeframe
4. Receive confirmation of your selection

## Requirements

- Python 3.7 or higher
- python-telegram-bot library
