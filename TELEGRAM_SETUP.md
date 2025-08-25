# Talent Search Chatbot - Telegram Setup

## Setting up the Telegram Bot

1. Open Telegram and search for @BotFather
2. Start a chat with BotFather and send `/start`
3. Send `/newbot` to create a new bot
4. Follow the prompts to:
   - Give your bot a name (e.g., "TalentSearchBot")
   - Choose a username for your bot (must end in "bot", e.g., "MyTalentSearchBot")
5. BotFather will provide you with a token that looks like:
   `123456789:AAGxcFoZueR3eHy-RhgHnVZ1yKuPo8r_BBc`

## Configuring the Application

1. Open the `.env` file in your project directory
2. Replace `YOUR_TELEGRAM_BOT_TOKEN_HERE` with your actual token from BotFather:
   ```
   TELEGRAM_BOT_TOKEN=123456789:AAGxcFoZueR3eHy-RhgHnVZ1yKuPo8r_BBc
   ```

## Running the Bot

### Development Mode (Polling)
For local development and testing:
```bash
python main.py telegram
```

### Webhook Mode (with ngrok)
For production or internet access:

1. First, install ngrok from https://ngrok.com/
2. Authenticate ngrok with your account token:
   ```bash
   ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
   ```
3. Start ngrok to expose port 8443:
   ```bash
   ngrok http 8443
   ```
4. Copy the HTTPS URL provided by ngrok (e.g., `https://abc123.ngrok-free.app`)
5. Update the `WEBHOOK_URL` in your `.env` file:
   ```
   WEBHOOK_URL=https://abc123.ngrok-free.app
   ```
6. Run the bot:
   ```bash
   python main.py telegram
   ```

## Testing the Bot

1. Open Telegram
2. Search for your bot by username
3. Start a chat and send `/start` to begin
4. Try queries like:
   - "5 sdm java Python" (5 people with Java as must-have and Python as nice-to-have)
   - "find Technical Leader with core banking experience"
   - "show me candidates with >5 years experience"