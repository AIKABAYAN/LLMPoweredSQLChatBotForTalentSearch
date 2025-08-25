"""
Test script for the Telegram bot functionality.
This script tests the core functionality without actually connecting to Telegram.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.intent_parser import call_ollama_intent
from src.query_executor import run_all_queries
from src.formatter import format_bucketed_sentences

def test_telegram_functionality():
    """Test the core Telegram bot functionality without connecting to Telegram"""
    print("Testing Telegram bot functionality...")
    
    # Test query
    test_query = "5 sdm java Python"
    print(f"Test query: {test_query}")
    
    # Parse the intent
    intent, prompt = call_ollama_intent(test_query)
    print(f"Parsed intent: {intent}")
    
    # Run the queries
    session_id = "test_tg_123"
    employees, raw, sql_time = run_all_queries(intent, session_id)
    print(f"Found {len(employees)} candidates")
    
    # Format the response
    if employees:
        # Get primary candidates
        lim = intent.get("limit", {}) or {}
        n_primary = int(lim.get("primary", 3))
        primary = employees[:n_primary]
        primary_tuples = [(e, e.get("score", 0)) for e in primary]
        
        # Format the response
        response = f"Found {len(primary)} candidates matching your criteria:\n\n"
        response += format_bucketed_sentences(primary_tuples)
        
        # Add timing info
        response += f"\n\nSearch completed in {sql_time:.2f}s"
        
        print("Formatted response:")
        # Handle encoding issues on Windows
        try:
            print(response)
        except UnicodeEncodeError:
            # Fallback to ASCII-only output
            print(response.encode('ascii', 'ignore').decode('ascii'))
    else:
        print("No candidates found")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_telegram_functionality()