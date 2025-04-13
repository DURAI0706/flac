from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
import os

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Google Sheets Setup
SERVICE_ACCOUNT_FILE = 'credentials.json'
SPREADSHEET_ID = '1cmEDOkDNXGubKNAV3TrcE2fDQvR0rHEyE9pWL1l_EMg'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Sheet names
SHEETS = {
    'complete': 'Sheet1',
    'date': 'Sheet2',
    'live': 'Sheet3'
}

# Authenticate Google Sheets
def get_worksheet(sheet_name):
    try:
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        return worksheet
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")
        return None

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Welcome to Tamil FLAC Search Bot!\n"
        "Use /search <mode> <keyword> to find music 🎶\n"
        "Available modes: complete, date, live\n\n"
        "Example: /search complete vijay"
    )
    await update.message.reply_text(message)

# Search Command
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
            reply = "\n\n".join(results[:5])  # Top 5
        else:
            reply = "❌ No results found."

        await update.message.reply_text(reply)
    except Exception as e:
        print(f"Error during search: {e}")
        await update.message.reply_text("⚠️ Something went wrong while searching.")

# Set up bot application
async def main():
    # Create the application instance with the bot token
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))

    # Start polling
    print("🤖 Bot is running... Press CTRL+C to stop.")
    await app.run_polling()

# Entry point for Gunicorn
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
