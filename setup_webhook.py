"""
Script to set up Telegram webhook using the provided ngrok URL
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the Telegram bot token and webhook URL from environment variables
# Force reading from .env file by not relying on system environment variables
TELEGRAM_BOT_TOKEN = None
WEBHOOK_URL = None

# Read directly from .env file
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            TELEGRAM_BOT_TOKEN = line.split('=', 1)[1].strip()
            # Remove any quotes if present
            TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN.strip('"').strip("'")
        elif line.startswith('WEBHOOK_URL='):
            WEBHOOK_URL = line.split('=', 1)[1].strip()
            # Remove any quotes if present
            WEBHOOK_URL = WEBHOOK_URL.strip('"').strip("'")

def set_telegram_webhook():
    """Set the Telegram bot webhook to the provided URL"""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
        return False
        
    if not WEBHOOK_URL:
        print("Error: WEBHOOK_URL not found in .env file")
        return False
    
    # Construct the full webhook URL for Telegram
    webhook_url = f"{WEBHOOK_URL}/telegram/webhook"
    
    # Telegram API endpoint for setting webhook
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    
    # Data to send to Telegram API
    data = {
        "url": webhook_url,
        "allowed_updates": ["message", "edited_message", "callback_query"]
    }
    
    try:
        print(f"Setting Telegram webhook to: {webhook_url}")
        print(f"Using token: {TELEGRAM_BOT_TOKEN}")
        response = requests.post(api_url, data=data)
        result = response.json()
        
        if result.get("ok"):
            print("Webhook set successfully!")
            print(f"Telegram API response: {result}")
            return True
        else:
            print(f"Failed to set webhook: {result}")
            return False
            
    except Exception as e:
        print(f"Error setting webhook: {str(e)}")
        return False

if __name__ == "__main__":
    print("Setting up Telegram webhook...")
    print(f"Telegram Bot Token: {TELEGRAM_BOT_TOKEN}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    
    success = set_telegram_webhook()
    
    if success:
        print("\nWebhook setup completed successfully!")
        print("Your Telegram bot should now be accessible via the ngrok URL.")
    else:
        print("\nWebhook setup failed!")
        print("Please check your token and URL, then try again.")