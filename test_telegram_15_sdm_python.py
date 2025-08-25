"""
Test script for the Telegram bot with specific prompt "15 sdm python".
This script tests the core functionality without actually connecting to Telegram.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.intent_parser import call_ollama_intent
from src.query_executor import run_all_queries
from src.formatter import format_bucketed_sentences
import json

def test_telegram_with_prompt_15_sdm_python():
    """Test the core Telegram bot functionality with prompt '15 sdm python'"""
    print("Testing Telegram bot functionality with prompt: '15 sdm python'")
    print("=" * 60)
    
    # Test query
    test_query = "15 sdm python"
    print(f"Test query: {test_query}")
    print()
    
    try:
        # Parse the intent
        print("Parsing intent...")
        intent, prompt = call_ollama_intent(test_query)
        print(f"Parsed intent: {json.dumps(intent, indent=2)}")
        print(f"Generated prompt: {prompt}")
        print()
        
        # Run the queries
        session_id = "test_tg_15_sdm_python"
        print("Executing queries...")
        employees, raw, sql_time = run_all_queries(intent, session_id)
        print(f"Found {len(employees)} candidates in {sql_time:.2f}s")
        print()
        
        # Show raw data if needed
        if raw:
            print(f"Raw query results: {len(raw)} rows")
            if len(raw) > 0:
                first_row = raw[0] if isinstance(raw, list) and len(raw) > 0 else None
                if first_row:
                    print("First row example:")
                    print(json.dumps(first_row, indent=2, default=str))
            print()
        
        # Format the response
        if employees:
            # Get primary candidates
            lim = intent.get("limit", {}) or {}
            n_primary = int(lim.get("primary", 15))  # Should be 15 based on the query
            primary = employees[:n_primary]
            primary_tuples = [(e, e.get("score", 0)) for e in primary]
            
            # Format the response
            response = f"Found {len(primary)} candidates matching your criteria:\n\n"
            response += format_bucketed_sentences(primary_tuples)
            
            # Add timing info
            response += f"\n\nSearch completed in {sql_time:.2f}s"
            
            print("Formatted response:")
            print("-" * 40)
            # Handle encoding issues on Windows
            try:
                print(response)
            except UnicodeEncodeError:
                # Fallback to ASCII-only output
                print(response.encode('ascii', 'ignore').decode('ascii'))
        else:
            print("No candidates found")
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("Test completed!")

def test_intent_parsing_only():
    """Test just the intent parsing with '15 sdm python'"""
    print("Testing intent parsing only with prompt: '15 sdm python'")
    print("=" * 60)
    
    test_query = "15 sdm python"
    print(f"Test query: {test_query}")
    
    try:
        intent, prompt = call_ollama_intent(test_query)
        print(f"Parsed intent: {json.dumps(intent, indent=2)}")
        print(f"Generated prompt: {prompt}")
    except Exception as e:
        print(f"Error during intent parsing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == "__main__":
    # Run the intent parsing test first
    test_intent_parsing_only()
    print()
    
    # Run the full test
    test_telegram_with_prompt_15_sdm_python()