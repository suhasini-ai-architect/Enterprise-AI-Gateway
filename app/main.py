from fastapi import FastAPI, HTTPException
import requests
import time
import uuid
from typing import Dict, Any

# Database Imports
from app.db.session import create_db_and_tables, log_event, ATMLog

# Guard Imports
from app.guards.loop import detector
from app.guards.cost import cost_guard
from app.guards.pii import pii_guard
from app.guards.injection import injection_shield
from app.guards.cache import semantic_cache

app = FastAPI(title="ATM - Enterprise AI Gateway")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "tinydolphin"

@app.on_event("startup")
def on_startup():
    print("🚀 Initializing Enterprise ATM Control Plane...")
    create_db_and_tables()
    print("✅ Database & Schema Ready.")
@app.post("/v1/proxy")
async def proxy_request(request: Dict[str, Any]):
    print("--- NEW REQUEST START ---")
    start_time = time.time()
    
    try:
        session_id = request.get("session_id", "test-id")
        raw_prompt = request.get("prompt", "")
        print(f"DEBUG: Data extracted for session {session_id}")

        # CHECK 1: Injection
        print("DEBUG: Checking Injection...")
        if injection_shield.is_malicious(raw_prompt):
            return {"status": "blocked", "reason": "security"}

        # CHECK 2: PII
        print("DEBUG: Checking PII...")
        prompt, pii = pii_guard.scrub(raw_prompt)

        # CHECK 3: LLM Connection
        print(f"DEBUG: Contacting Ollama at {OLLAMA_URL}...")
       
        resp = requests.post(
        OLLAMA_URL, 
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, 
        timeout=180)

        resp.raise_for_status()
        llm_response = resp.json().get("response", "")
        print("DEBUG: Ollama responded successfully")

        # CHECK 4: Database Logging
        print("DEBUG: Attempting Database Log...")
        log_event(ATMLog(
            session_id=session_id, prompt=prompt, response=llm_response, 
            status="passed", tokens=0, latency=time.time()-start_time
        ))
        print("DEBUG: Log saved to DB")

        return {"response": llm_response}

    except Exception as e:
        print(f"❌ ARCHITECT ALERT - Error found: {str(e)}")
        import traceback
        traceback.print_exc() # This prints the EXACT line number of the crash
        return {"error": "Look at the Uvicorn terminal for the Traceback"}