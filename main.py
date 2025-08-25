"""
Talent Search Chatbot - Refactored Version

This is the main entry point for the application.
The application has been refactored into multiple modules:
- config.py: Configuration and logging setup
- database.py: Database connection
- intent_parser.py: Intent parsing functionality
- sql_builder.py: SQL query building
- query_executor.py: Query execution and data merging
- scoring.py: Employee scoring algorithms
- formatter.py: Result formatting
- logger_helper.py: Logging helpers
- ui.py: UI application
- telegram_bot.py: Telegram bot integration
- main.py: Main application entry point (in src directory)

To run the application:
- For UI: python main.py
- For Telegram bot (polling): python main.py telegram
- For Telegram bot (webhook with ngrok): python main.py webhook

To use the Telegram bot:
1. Create a bot with @BotFather on Telegram
2. Get your bot token
3. Update the TELEGRAM_BOT_TOKEN in your .env file
4. Run with 'python main.py telegram' or 'python main.py webhook'
"""

import sys
import tkinter as tk
from src.config import logger

def run_ui():
    """Run the tkinter UI application"""
    from src.ui import App
    root = tk.Tk()
    app = App(root)
    logger.info("Talent Search Chatbot UI started.")
    root.mainloop()

def run_telegram_bot():
    """Run the Telegram bot"""
    logger.info("Starting Telegram bot...")
    from src.telegram_bot import main as telegram_main
    telegram_main()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "telegram":
        run_telegram_bot()
    elif len(sys.argv) > 1 and sys.argv[1] == "webhook":
        # Run the webhook version
        logger.info("Starting Telegram bot with webhook...")
        from main_webhook import start_with_ngrok
        start_with_ngrok()
    else:
        run_ui()