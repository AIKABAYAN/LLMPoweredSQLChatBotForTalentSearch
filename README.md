# Talent Search Chatbot

An intelligent chatbot for searching and filtering talent profiles using natural language processing and SQL queries.

## Features

- Natural language processing for talent search queries
- Smart candidate matching with scoring algorithms
- Multiple interface options:
  - Desktop UI application
  - Telegram bot integration
- PostgreSQL database backend
- AI-powered intent parsing with Ollama

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Ollama with qwen3 models
- Telegram account (for bot functionality)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd LLMPoweredSQLChatBot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   - Create a PostgreSQL database
   - Update connection details in `.env` file

4. Configure Ollama:
   - Install Ollama from https://ollama.com/
   - Pull required models:
     ```bash
     ollama pull qwen3:4b-instruct
     ollama pull qwen3:0.6b
     ```

5. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update values in `.env` with your configuration

## Running the Application

### UI Mode
```bash
python main.py
```

### Telegram Bot
Follow the instructions in [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for setting up and running the Telegram bot.

## Usage

### UI Application
The desktop UI provides a chat-like interface for interacting with the talent search system.

### Telegram Bot
The Telegram bot allows you to search for candidates using natural language queries:
- "5 sdm java Python" (5 people with Java as must-have and Python as nice-to-have)
- "find Technical Leader with core banking experience"
- "show me candidates with >5 years experience"

### Query Syntax
- Capitalized skills (Java) = must-have
- Lowercase skills (python) = nice-to-have
- Numbers indicate quantity of candidates to return

## Project Structure

```
src/
├── config.py          # Configuration and logging setup
├── database.py        # Database connection
├── intent_parser.py   # Intent parsing functionality
├── sql_builder.py     # SQL query building
├── query_executor.py  # Query execution and data merging
├── scoring.py         # Employee scoring algorithms
├── formatter.py       # Result formatting
├── logger_helper.py   # Logging helpers
├── ui.py              # UI application
├── telegram_bot.py    # Telegram bot integration
└── main.py            # Main application entry point
```

## Technologies Used

- Python
- PostgreSQL
- Ollama (qwen3 models)
- Tkinter (UI)
- python-telegram-bot
- Flask (webhook server)