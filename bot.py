from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
import os
import json
from dotenv import load_dotenv
from flask import Flask, request

# Load environment variables from .env file (for local development)
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Google Sheets Setup
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Sheet names
SHEETS = {
    'complete': 'Sheet1',
    'date': 'Sheet2',
    'live': 'Sheet3'
}

# Create a Flask web server
app = Flask(__name__)

# Initialize bot application
bot_app = Application.builder().token(BOT_TOKEN).build()

# Authenticate Google Sheets
def get_worksheet(sheet_name):
    try:
        # If running on Render, use environment variable
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        
        gc = gspread.authorize(credentials)
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        return worksheet
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Welcome to Tamil FLAC Search Bot!\n"
        "Use /search <mode> <keyword> to find music 🎶\n"
        "Available modes: complete, date, live\n\n"
        "Example: /search complete vijay"
    )
    await update.message.reply_text(message)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❗Usage: /search <mode> <keyword>\nExample: /search live anirudh")
        return

    mode = context.args[0].lower()
    keyword = ' '.join(context.args[1:]).lower()

    if mode not in SHEETS:
        await update.message.reply_text("❗Invalid mode. Choose from: complete, date, live")
        return

    worksheet = get_worksheet(SHEETS[mode])
    if not worksheet:
        await update.message.reply_text("❌ Error accessing Google Sheet.")
        return

    try:
        values = worksheet.get_all_values()
        data_rows = values[3:] if len(values) > 3 else []  # Skip headers

        results = []
        for row in data_rows:
            if len(row) >= 2 and keyword in row[1].lower():
                results.append(f"{row[0]} — {row[1]}")

        if results:
            # Limit message size for Telegram
            if len(results) > 5:
                reply = f"Found {len(results)} matches. Here are the top 5:\n\n"
                reply += "\n\n".join(results[:5])
            else:
                reply = "\n\n".join(results)
        else:
            reply = "❌ No results found."

        await update.message.reply_text(reply)
    except Exception as e:
        print(f"Error during search: {e}")
        await update.message.reply_text("⚠️ Something went wrong while searching.")

# Register bot handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("search", search))

# Flask route for webhook
@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    await bot_app.process_update(update)
    return 'OK'

# Health check endpoint
@app.route('/')
def home():
    return "Tamil FLAC Search Bot is running!"

# Set webhook URL
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if not render_url:
        return "Error: RENDER_EXTERNAL_URL not set!"
    
    webhook_url = f"{render_url}/webhook/{BOT_TOKEN}"
    try:
        bot_app.bot.set_webhook(webhook_url)
        return f"Webhook set to {webhook_url}"
    except Exception as e:
        return f"Error setting webhook: {e}"

if __name__ == '__main__':
    # Get port from environment variable or default to 10000
    port = int(os.environ.get('PORT', 10000))
    
    # Set the webhook on startup
    if os.environ.get('RENDER_EXTERNAL_URL'):
        webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook/{BOT_TOKEN}"
        bot_app.bot.set_webhook(webhook_url)
        print(f"Webhook set to {webhook_url}")
    else:
        print("Running locally - webhook not set")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port)
