"""
Flask service for the Talent Search Chatbot
This service exposes the chatbot functionality via REST API endpoints.
"""
import os
import sys
import json
from flask import Flask, request, jsonify
from src.intent_parser import call_ollama_intent
from src.query_executor import run_all_queries
from src.config import logger

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

@app.route("/")
def root():
    """Root endpoint with service information"""
    return jsonify({
        "message": "Talent Search Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "POST /search": "Search for candidates using natural language queries",
            "GET /health": "Health check endpoint"
        }
    })

@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

@app.route("/search", methods=["POST"])
def search_candidates():
    """
    Search for candidates using natural language queries
    
    Example request:
    {
        "query": "15 sdm python",
        "session_id": "api_user"
    }
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        query = data.get("query", "")
        session_id = data.get("session_id", "api_user")
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        logger.info(f"[{session_id}] API search query: {query}")
        
        # Parse the intent
        intent, prompt = call_ollama_intent(query)
        logger.info(f"[{session_id}] Parsed intent: {intent}")
        
        # Run the queries
        employees, raw, sql_time = run_all_queries(intent, session_id)
        
        # Format the response
        if not employees:
            return jsonify({
                "query": query,
                "candidates": [],
                "total_found": 0,
                "search_time": sql_time,
                "message": "No candidates found matching your criteria. Try adjusting your search terms."
            })
            
        # Get primary candidates
        lim = intent.get("limit", {}) or {}
        n_primary = int(lim.get("primary", 3))
        primary = employees[:n_primary]
        
        # Create response message
        message = f"Found {len(primary)} candidates matching your criteria"
        
        return jsonify({
            "query": query,
            "candidates": primary,
            "total_found": len(primary),
            "search_time": sql_time,
            "message": message
        })
        
    except Exception as e:
        logger.error(f"[{session_id}] Error processing search: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error processing search: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7777, debug=True)