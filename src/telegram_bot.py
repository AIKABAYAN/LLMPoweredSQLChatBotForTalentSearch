import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import InvalidToken
from src.intent_parser import call_ollama_intent
from src.query_executor import run_all_queries
from src.formatter import format_bucketed_sentences
from src.config import logger

# Load environment variables from .env file explicitly
load_dotenv('.env')

# Get the bot token from .env file directly
TELEGRAM_BOT_TOKEN = None
WEBHOOK_URL = None

# Read directly from .env file
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                TELEGRAM_BOT_TOKEN = line.split('=', 1)[1].strip()
                # Remove any quotes if present
                TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN.strip('"').strip("'").strip()
            elif line.startswith('WEBHOOK_URL='):
                WEBHOOK_URL = line.split('=', 1)[1].strip()
                # Remove any quotes if present
                WEBHOOK_URL = WEBHOOK_URL.strip('"').strip("'").strip()
except Exception as e:
    print(f"Error reading .env file: {e}")

# Debug: Print the token being used
print(f"Using TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN}")
print(f"Using WEBHOOK_URL: {WEBHOOK_URL}")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
bot_logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! I'm SikabayanBot, your talent search assistant. "
        "You can search for candidates by sending me queries like:\n\n"
        "• '5 sdm java Python' (5 people with Java as must-have and Python as nice-to-have)\n"
        "• 'find Technical Leader with core banking experience'\n"
        "• 'show me candidates with >5 years experience'\n\n"
        "How can I help you find talent today?"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "I can help you search for talent! Send me queries like:\n\n"
        "• '5 sdm java Python' - Find 5 people with Java (must-have) and Python (nice-to-have)\n"
        "• 'find Technical Leader with core banking experience'\n"
        "• 'show me candidates with >5 years experience'\n"
        "• 'recommend someone with spring boot skills'\n\n"
        "Capitalization matters:\n"
        "• Capitalized skills (Java) = must-have\n"
        "• Lowercase skills (python) = nice-to-have"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    user_query = update.message.text
    user = update.effective_user
    session_id = f"tg_{user.id}"
    
    bot_logger.info(f"[{session_id}] User {user.first_name} ({user.id}) query: {user_query}")
    await update.message.reply_text("🔍 Searching for candidates... Please wait.")
    
    try:
        # Parse the intent
        intent, prompt = call_ollama_intent(user_query)
        bot_logger.info(f"[{session_id}] Parsed intent: {intent}")
        
        # Run the queries
        employees, raw, sql_time = run_all_queries(intent, session_id)
        
        # Format the response
        if not employees:
            await update.message.reply_text("I couldn't find any candidates matching your criteria. Try adjusting your search terms.")
            return
            
        # Get primary candidates
        lim = intent.get("limit", {}) or {}
        n_primary = int(lim.get("primary", 3))
        primary = employees[:n_primary]
        primary_tuples = [(e, e.get("score", 0)) for e in primary]
        
        # Format the response
        response = f"✅ Found {len(primary)} candidates matching your criteria:\n\n"
        response += format_bucketed_sentences(primary_tuples)
        
        # Add timing info
        response += f"\n\n⏱️ Search completed in {sql_time:.2f}s"
        
        await update.message.reply_text(response)
        
    except Exception as e:
        bot_logger.error(f"[{session_id}] Error processing query: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. "
            "Please try again or contact support."
        )

def main() -> None:
    """Start the bot."""
    # Validate token
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set in the environment variables")
        print("To use the Telegram bot, you need to:")
        print("1. Create a bot with @BotFather on Telegram")
        print("2. Get your bot token")
        print("3. Update the TELEGRAM_BOT_TOKEN in your .env file")
        print("4. For webhook mode, set WEBHOOK_URL in .env file")
        print("5. Restart the application with 'python main.py telegram'")
        return
        
    # Validate token format (should be in format "123456789:ABCdefGhIjKlMnOpQRsTUVwxyZ")
    if len(TELEGRAM_BOT_TOKEN.split(':')) != 2:
        print(f"Invalid TELEGRAM_BOT_TOKEN format: {TELEGRAM_BOT_TOKEN}")
        print("Token should be in format: 123456789:ABCdefGhIjKlMnOpQRsTUVwxyZ")
        return

    try:
        # Create the Application and pass it your bot's token
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Register handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Run the bot
        bot_logger.info("Telegram bot starting...")
        
        if WEBHOOK_URL:
            # Webhook mode (for production/Internet access)
            bot_logger.info(f"Running in webhook mode at {WEBHOOK_URL}")
            application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                url_path="/telegram/webhook",
                webhook_url=f"{WEBHOOK_URL}/telegram/webhook"
            )
        else:
            # Polling mode (for development)
            bot_logger.info("Note: Bot will run in polling mode. Send messages to your bot on Telegram.")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
            bot_logger.info("Telegram bot started successfully")
        
    except InvalidToken:
        print("The provided TELEGRAM_BOT_TOKEN is invalid.")
        print("Please check your token with @BotFather on Telegram and update it in your .env file.")
    except Exception as e:
        bot_logger.error(f"Failed to start Telegram bot: {str(e)}", exc_info=True)
        print("Telegram bot could not start due to an error.")
        print("Check the logs for more details.")

if __name__ == "__main__":
    main()