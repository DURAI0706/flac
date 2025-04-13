from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
import os
import json
from dotenv import load_dotenv
from flask import Flask
import threading

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

@app.route('/')
def home():
    return "Tamil FLAC Search Bot is running!"

def run_flask():
    # Get port from environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

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

# In your main() function, update the polling method to use webhook mode instead:

def main():
    # Set up bot application
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("search", search))

    print("🤖 Bot is running...")
    
    # Start Flask in a separate thread
    threading_flask = threading.Thread(target=run_flask)
    threading_flask.daemon = True
    threading_flask.start()
    
    # Run the Telegram bot with a longer timeout
    bot_app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
