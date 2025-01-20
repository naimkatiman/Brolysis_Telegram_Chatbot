import logging
import os
from dotenv import load_dotenv
import requests
from io import BytesIO
from PIL import Image
import openai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Load environment variables
load_dotenv()

# Configure API keys
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHART_IMG_API_KEY = os.getenv('CHART_IMG_API_KEY')
openai.api_key = os.getenv('OPENAI_API_KEY')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define asset and timeframe options
ASSETS = {
    'xauusd': 'XAU/USD (Gold)',
    'btc': 'Bitcoin (BTC)',
    'dxy': 'USD Index (DXY)',
    'wti': 'Crude Oil (WTI)',
    'ndx': 'Nasdaq (NDX)'
}

TIMEFRAMES = {
    '1m': '1-minute',
    '5m': '5-minute',
    '15m': '15-minute',
    '1h': '1-hour',
    '1d': '1-day'
}

# Store user selections
user_selections = {}

async def get_chart_image(symbol: str, timeframe: str) -> BytesIO:
    """Fetch chart image from the API."""
    # Convert symbol and timeframe to API-compatible format
    symbol_map = {
        'xauusd': 'XAUUSD',
        'btc': 'BTCUSD',
        'dxy': 'DXY',
        'wti': 'WTIUSD',
        'ndx': 'NDX'
    }
    
    api_symbol = symbol_map.get(symbol, symbol.upper())
    api_url = f"https://api.chart-img.com/v2/tradingview/advanced-chart"
    
    # Prepare the request payload with technical indicators
    payload = {
        "symbol": api_symbol,
        "interval": timeframe,
        "theme": "dark",
        "height": 800,  # Increased height to accommodate indicators
        "width": 1200,
        "studies": [
            # Add Volume with custom colors
            {
                "name": "Volume",
                "forceOverlay": True,
                "override": {
                    "Volume.color.0": "rgba(247,82,95,0.3)",  # Red volume
                    "Volume.color.1": "rgba(34,171,148,0.3)"   # Green volume
                }
            },
            # Add RSI with standard settings
            {
                "name": "Relative Strength Index",
                "input": {
                    "length": 14  # Standard RSI period
                },
                "override": {
                    "Plot.color": "rgb(33,150,243)",  # Blue line
                    "UpperLimit.value": 70,  # Overbought level
                    "LowerLimit.value": 30   # Oversold level
                }
            },
            # Add SuperTrend
            {
                "name": "Supertrend",
                "input": {
                    "Factor": 3,
                    "Period": 10
                },
                "override": {
                    "Up Trend.color": "rgb(8,153,129)",    # Green for uptrend
                    "Down Trend.color": "rgb(242,54,69)"   # Red for downtrend
                }
            }
        ]
    }
    
    headers = {
        "x-api-key": CHART_IMG_API_KEY,
        "content-type": "application/json"
    }
    
    response = requests.post(api_url, json=payload, headers=headers)
    response.raise_for_status()
    
    return BytesIO(response.content)

async def analyze_chart(image_data: BytesIO) -> str:
    """Analyze chart using OpenAI Vision API."""
    try:
        # Convert image to base64 if needed
        image = Image.open(image_data)
        
        response = openai.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Please analyze this financial chart focusing on:
1. SuperTrend direction and potential trend changes
2. Volume analysis - Is volume confirming the trend?
3. RSI (14) - Identify overbought (>70) or oversold (<30) conditions
4. Overall market structure and key price levels

Please provide a concise analysis with actionable insights."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data,
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error analyzing chart: {str(e)}")
        return "Sorry, I couldn't analyze the chart at this moment. Please try again later."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and asset selection buttons when /start is issued."""
    keyboard = [
        [InlineKeyboardButton(text, callback_data=f"asset_{key}")]
        for key, text in ASSETS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        "👋 Welcome to the Financial Market Analysis Bot!\n\n"
        "I can help you analyze various financial assets using AI-powered technical analysis.\n\n"
        "Please select an asset you're interested in:"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def handle_asset_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, asset_key: str) -> None:
    """Handle asset selection and show timeframe options."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Store the asset selection
    if user_id not in user_selections:
        user_selections[user_id] = {}
    user_selections[user_id]['asset'] = asset_key
    
    # Create timeframe selection buttons
    keyboard = [
        [InlineKeyboardButton(text, callback_data=f"timeframe_{key}")]
        for key, text in TIMEFRAMES.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"You selected {ASSETS[asset_key]}.\nNow, please choose a timeframe:",
        reply_markup=reply_markup
    )

async def handle_timeframe_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe_key: str) -> None:
    """Handle timeframe selection, fetch chart, and provide analysis."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Store the timeframe selection
    user_selections[user_id]['timeframe'] = timeframe_key
    
    # Get the complete selection
    asset = user_selections[user_id]['asset']
    
    await query.edit_message_text("Fetching and analyzing the chart... Please wait.")
    
    try:
        # Get chart image
        chart_data = await get_chart_image(asset, timeframe_key)
        
        # Send chart image
        await context.bot.send_photo(
            chat_id=user_id,
            photo=chart_data,
            caption=f"Chart for {ASSETS[asset]} ({TIMEFRAMES[timeframe_key]})"
        )
        
        # Analyze chart
        analysis = await analyze_chart(chart_data)
        
        # Send analysis
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📊 Analysis:\n\n{analysis}\n\nTo analyze another asset, use /start"
        )
        
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text="Sorry, there was an error processing your request. Please try again later."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Parse the callback data
    data = query.data
    if data.startswith('asset_'):
        asset_key = data.replace('asset_', '')
        await handle_asset_selection(update, context, asset_key)
    elif data.startswith('timeframe_'):
        timeframe_key = data.replace('timeframe_', '')
        await handle_timeframe_selection(update, context, timeframe_key)

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    await update.message.reply_text(
        "Sorry, I didn't understand that. Please use the buttons or valid commands.\n"
        "Use /start to begin interaction with the bot."
    )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
