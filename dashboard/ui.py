import streamlit as st
import time
import pandas as pd
import re
import hashlib
import sqlite3
import requests
import os
from datetime import datetime

# --- CONFIGURATION (Public-Safe Defaults) ---
# In production, these would be set via Azure Key Vault or .env
DB_PATH = os.getenv("GUARDIAN_DB_PATH", "guardian_mesh.db")
ADMIN_PASS = os.getenv("GUARDIAN_ADMIN_PASS", "admin123")

# --- 0. AUTHENTICATION LAYER (Identity Gatekeeper) ---
def check_password():
    """Prototype Login. Production version integrates with Azure AD / OIDC."""
    def password_entered():
        if st.session_state["password"] == ADMIN_PASS:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🛡️ Guardian-Mesh Login")
        st.text_input("Enterprise Access Key", type="password", on_change=password_entered, key="password")
        st.info("Demo Mode: Use 'admin123'")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enterprise Access Key", type="password", on_change=password_entered, key="password")
        st.error("❌ Access Denied.")
        return False
    return True

if not check_password():
    st.stop()

# --- 1. DATABASE LAYER (Identity-Aware Persistence) ---
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS semantic_cache 
                 (query_hash TEXT PRIMARY KEY, response TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_ledger 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, 
                  user_id TEXT, 
                  status TEXT, 
                  latency TEXT, 
                  savings REAL)''')
    conn.commit()
    return conn

db_conn = init_db()

def get_query_hash(text):
    return hashlib.md5(text.lower().strip().encode()).hexdigest()

# --- 2. MULTI-MODEL ROUTING LOGIC ---
def call_llm(payload, provider):
    """Routing logic for Enterprise AI Nodes."""
    if provider == "Local Edge (Ollama)":
        try:
            # We use a 60s timeout to handle initial model loading on laptops
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2:1b", "prompt": payload, "stream": False},
                timeout=60 
            )
            return response.json().get("response", "Error: Empty Response")
        except Exception as e:
            return f"Node Offline: Ensure Ollama is running llama3.2:1b locally."
    
    # Placeholders for Cloud Provider Logic
    elif provider == "Azure OpenAI (GPT-4)":
        return f"[MOCKED] Azure Cloud securely processed: {payload[:30]}..."
    
    return "Routing... (Integration Pending)"

def guardian_controller(user_input, mode, provider):
    start_time = time.perf_counter()
    query_id = get_query_hash(user_input)
    
    # 1. Semantic Cache Check
    c = db_conn.cursor()
    c.execute("SELECT response FROM semantic_cache WHERE query_hash = ?", (query_id,))
    row = c.fetchone()
    if row:
        return {"is_cache_hit": True, "response": row[0], "latency": "0.05ms", "scrubbed": user_input}

    # 2. PII Interception Pipeline
    # Note: Public version uses Regex. Enterprise version supports NER (Named Entity Recognition).
    patterns = {"EMAIL": r'\S+@\S+', "CREDIT_CARD": r'\b\d{13,16}\b'}
    processed_text = user_input
    found_pii = False
    
    for label, pat in patterns.items():
        if re.search(pat, user_input):
            found_pii = True
            if mode == "Strict":
                return {"is_blocked": True, "response": "POLICY BLOCK", "latency": "0ms", "scrubbed": "[BLOCKED]"}
            processed_text = re.sub(pat, f"[{label}_MASKED]", processed_text)

    # 3. Secure Inference
    response = call_llm(processed_text, provider)
    
    # 4. Save to Cache (Only for Clean queries)
    if not found_pii and not response.startswith("Node Offline"):
        c.execute("INSERT OR REPLACE INTO semantic_cache VALUES (?,?)", (query_id, response))
        db_conn.commit()

    latency = (time.perf_counter() - start_time) * 1000
    return {
        "is_cache_hit": False,
        "is_blocked": "BLOCKED" in processed_text or mode == "Strict" and found_pii,
        "response": response,
        "latency": f"{latency:.2f}ms",
        "scrubbed": processed_text
    }

# --- 3. EXECUTIVE DASHBOARD UI ---
st.set_page_config(page_title="Guardian-Mesh AI", page_icon="🛡️", layout="wide")

with st.sidebar:
    st.title("🛡️ Guardian-Mesh")
    st.caption("v1.0 - Enterprise Control Plane")
    st.divider()
    st.write("👤 **Identity:** Admin_Suhasini")
    mode = st.radio("Enforcement Policy", ["Strict", "Standard", "Audit Only"], index=1)
    provider = st.selectbox("AI Node", ["Local Edge (Ollama)", "Azure OpenAI (GPT-4)", "AWS Bedrock", "GCP Vertex"])
    
    if st.button("Purge System Data"):
        c = db_conn.cursor()
        c.execute("DELETE FROM semantic_cache"); c.execute("DELETE FROM audit_ledger")
        db_conn.commit()
        st.rerun()

st.title("AI Governance Dashboard")

# --- ROI ANALYTICS ENGINE ---
c = db_conn.cursor()
c.execute("SELECT timestamp, savings FROM audit_ledger ORDER BY id ASC")
history = c.fetchall()

if history:
    df_history = pd.DataFrame(history, columns=['Time', 'Savings'])
    df_history['Cumulative'] = df_history['Savings'].cumsum()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Security Pipeline", "ACTIVE")
    m2.metric("Total ROI", f"${df_history['Cumulative'].iloc[-1]:.4f}")
    m3.metric("Cache Efficiency", f"{len(df_history[df_history['Savings'] >= 0.05])} Hits")
    m4.metric("Identity Auth", "VERIFIED")

    st.subheader("FinOps Savings Trend")
    st.line_chart(df_history.set_index('Time')['Cumulative'])
else:
    st.info("System Ready. Awaiting incoming traffic to generate ROI data...")

st.divider()

# --- INTERACTION PIPELINE ---
if prompt := st.chat_input("Input AI Prompt..."):
    col_in, col_mesh, col_out = st.columns(3)
    
    result = guardian_controller(prompt, mode, provider)
    
    with col_in:
        st.caption("📥 RAW INPUT")
        st.info(prompt)
    with col_mesh:
        st.caption("🛡️ MESH INTERCEPTION")
        if result.get("is_blocked"): st.error("🚨 BLOCKED: Policy Violation")
        elif result.get("is_cache_hit"): st.success("⚡ CACHE HIT (Local Persistence)")
        else: st.warning(f"🔍 SCRUBBED: {result['scrubbed']}")
    with col_out:
        st.caption("📤 SECURE RESPONSE")
        st.success(result["response"])

    # Identity-Aware Logging
    status = "CACHE_HIT" if result.get("is_cache_hit") else ("BLOCKED" if result.get("is_blocked") else "CLEAN")
    savings = 0.05 if status == "CACHE_HIT" else (0.00 if status == "BLOCKED" else 0.01)
    
   # Ensure this block is closed correctly:
    c.execute("INSERT INTO audit_ledger (timestamp, user_id, status, latency, savings) VALUES (?,?,?,?,?)",
              (datetime.now().strftime("%H:%M:%S"), "Admin_Suhasini", status, result["latency"], savings))
    db_conn.commit()
    
    # This button helps refresh the UI state after the DB update
    st.button("Update Dashboard")

# --- 4. ENTERPRISE AUDIT LEDGER ---
st.divider()
st.subheader("📋 Enterprise Audit Ledger")
c.execute("SELECT timestamp, user_id, status, latency FROM audit_ledger ORDER BY id DESC LIMIT 5")
logs = pd.DataFrame(c.fetchall(), columns=['Time', 'User ID', 'Status', 'Latency'])
st.dataframe(logs, use_container_width=True, hide_index=True)