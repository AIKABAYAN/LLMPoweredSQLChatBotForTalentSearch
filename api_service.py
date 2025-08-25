"""
FastAPI service for the Talent Search Chatbot
This service exposes the chatbot functionality via REST API endpoints.
"""
import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
import uvicorn
import json
from src.intent_parser import call_ollama_intent
from src.query_executor import run_all_queries
from src.formatter import format_bucketed_sentences, format_employee_summary
from src.config import logger

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Talent Search Chatbot API",
    description="API for searching and filtering talent profiles using natural language processing",
    version="1.0.0"
)

class SearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = "api_user"

class CandidateSummary(BaseModel):
    id: Optional[str] = None
    name: str
    experience_years: float
    primary_skills: List[str]
    secondary_skills: List[str]
    score: float
    role: Optional[str] = None
    education: Optional[str] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }

class SearchResult(BaseModel):
    query: str
    candidates: List[CandidateSummary]
    total_found: int
    search_time_seconds: float
    message: str
    summary: str

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "message": "Talent Search Chatbot API",
        "version": "1.0.0",
        "description": "Search for talent using natural language queries",
        "endpoints": {
            "POST /search": "Search for candidates using natural language queries",
            "GET /health": "Health check endpoint"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Talent Search Chatbot API"}

@app.post("/search", response_model=SearchResult)
async def search_candidates(request: SearchRequest):
    """
    Search for candidates using natural language queries
    
    Examples:
    - "5 sdm java Python" (5 people with Java as must-have and Python as nice-to-have)
    - "find Technical Leader with core banking experience"
    - "show me candidates with >5 years experience"
    - "15 sdm python" (15 software developers with Python as must-have skill)
    """
    try:
        logger.info(f"[{request.session_id}] API search query: {request.query}")
        
        # Parse the intent
        intent, prompt = call_ollama_intent(request.query)
        logger.info(f"[{request.session_id}] Parsed intent: {intent}")
        
        # Run the queries
        employees, raw, sql_time = run_all_queries(intent, request.session_id)
        
        # Handle case when no candidates found
        if not employees:
            return SearchResult(
                query=request.query,
                candidates=[],
                total_found=0,
                search_time_seconds=sql_time,
                message="No candidates found matching your criteria. Try adjusting your search terms.",
                summary="No candidates matched your search criteria."
            )
            
        # Get primary candidates based on limit in intent
        lim = intent.get("limit", {}) or {}
        n_primary = int(lim.get("primary", 3))
        primary = employees[:n_primary]
        
        # Format candidates using the same formatter as UI
        # Use individual summaries like the UI does with employee_summary_var=True
        formatted_summaries = []
        for emp in primary:
            try:
                summary = format_employee_summary(emp, intent)
                formatted_summaries.append(summary)
            except Exception as e:
                logger.error(f"Error formatting employee summary: {str(e)}", exc_info=True)
                formatted_summaries.append("Error formatting candidate summary")
        
        # Join all summaries with newlines (like UI does)
        formatted_response = "\n".join(formatted_summaries)
        
        # Convert employees to CandidateSummary objects for structured data
        candidates = []
        for employee in primary:
            try:
                # Extract skills
                primary_skills = []
                secondary_skills = []
                
                # Get skills from various fields
                if "skills" in employee and employee["skills"]:
                    if isinstance(employee["skills"], str):
                        primary_skills.extend(employee["skills"].split())
                    elif isinstance(employee["skills"], list):
                        primary_skills.extend([str(s) for s in employee["skills"]])
                    else:
                        primary_skills.append(str(employee["skills"]))
                
                if "primary_skills" in employee and employee["primary_skills"]:
                    if isinstance(employee["primary_skills"], str):
                        primary_skills.extend(employee["primary_skills"].split())
                    elif isinstance(employee["primary_skills"], list):
                        primary_skills.extend([str(s) for s in employee["primary_skills"]])
                    else:
                        primary_skills.append(str(employee["primary_skills"]))
                        
                if "secondary_skills" in employee and employee["secondary_skills"]:
                    if isinstance(employee["secondary_skills"], str):
                        secondary_skills.extend(employee["secondary_skills"].split())
                    elif isinstance(employee["secondary_skills"], list):
                        secondary_skills.extend([str(s) for s in employee["secondary_skills"]])
                    else:
                        secondary_skills.append(str(employee["secondary_skills"]))
                
                # Safely extract other fields
                def safe_str(value):
                    if value is None:
                        return None
                    if isinstance(value, (list, dict)):
                        return str(value)
                    return str(value)
                
                def safe_float(value, default=0.0):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                # Create candidate summary
                candidate = CandidateSummary(
                    id=safe_str(employee.get("employee_id") or employee.get("id")),
                    name=safe_str(employee.get("name", employee.get("full_name", "Unknown Candidate"))),
                    experience_years=safe_float(employee.get("experience", 0.0)),
                    primary_skills=list(set([safe_str(s) for s in primary_skills if s])) if primary_skills else [],
                    secondary_skills=list(set([safe_str(s) for s in secondary_skills if s])) if secondary_skills else [],
                    score=safe_float(employee.get("score", 0.0)),
                    role=safe_str(employee.get("role") or employee.get("position")),
                    education=safe_str(employee.get("education") or employee.get("highest_education"))
                )
                candidates.append(candidate)
            except Exception as e:
                logger.error(f"Error processing candidate: {str(e)}", exc_info=True)
                # Create a minimal candidate even if there are errors
                candidate = CandidateSummary(
                    name="Error Processing Candidate",
                    experience_years=0.0,
                    primary_skills=[],
                    secondary_skills=[],
                    score=0.0
                )
                candidates.append(candidate)
        
        # Create response message
        message = f"Found {len(candidates)} candidates matching your criteria"
        
        # Use the formatted response as summary (same as UI)
        summary = formatted_response
        
        return SearchResult(
            query=request.query,
            candidates=candidates,
            total_found=len(candidates),
            search_time_seconds=sql_time,
            message=message,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"[{request.session_id}] Error processing search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing search: {str(e)}")

# Example of how to run the service
if __name__ == "__main__":
    print("Starting Talent Search Chatbot API on http://localhost:7777")
    print("API Documentation available at http://localhost:7777/docs")
    uvicorn.run("api_service:app", host="0.0.0.0", port=7777, log_level="info")