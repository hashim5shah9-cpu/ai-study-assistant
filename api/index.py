import os
import sys
import requests
import io 
import json
import re
import base64
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Safe imports for optional libraries
try:
    from groq import Groq
except BaseException:
    Groq = None

try:
    from pypdf import PdfReader
except BaseException:
    PdfReader = None

try:
    from pptx import Presentation
except BaseException:
    Presentation = None

try:
    import docx2txt
except BaseException:
    docx2txt = None

try:
    from google import genai
    from google.genai import types
except BaseException:
    genai = None
    types = None

# Ensure api directory is in sys.path
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

try:
    from database import get_db_connection
except BaseException:
    get_db_connection = lambda: None


app = FastAPI()

# 1. CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "online", "message": "Vercel Python serverless backend is live and working!"}


# ====================================================
# API KEYS CONFIGURATION (LOAD FROM ENV)
# ====================================================
GROQ_KEY = os.getenv("GROQ_KEY", "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")      
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "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")  
GEMINI_KEY = os.getenv("GEMINI_KEY", "AQ.Ab8RN6K5igFNFB0ayrDT3fELaPbHUh0eOeZI75jx1-CG2f5AvA")


# Request Models
class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    email: str = "guest@gmail.com"


# SIGNUP ENDPOINT
@app.post("/auth/signup")
async def signup(payload: SignupRequest):
    db = get_db_connection()
    if not db:
        raise HTTPException(status_code=500, detail="Database connection failure")
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (payload.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email pehle se registered hai!")
        
        query = "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)"
        cursor.execute(query, (payload.username, payload.email, payload.password))
        db.commit()
        cursor.close()
        return {"message": "Account successfully created!"}
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass

# LOGIN ENDPOINT
@app.post("/auth/login")
async def login(payload: LoginRequest):
    db = get_db_connection()
    if not db:
        raise HTTPException(status_code=500, detail="Database connection failure")
    try:
        cursor = db.cursor(dictionary=True)
        query = "SELECT user_id, username, email FROM users WHERE email = %s AND password_hash = %s"
        cursor.execute(query, (payload.email, payload.password))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            raise HTTPException(status_code=401, detail="Ghalat email ya password!")
            
        return {
            "token": "fake-jwt-token",
            "email": user['email'],
            "username": user['username']
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass


# =====================================================================
# AI ENGINE ENGINES
# =====================================================================
def call_openrouter_api(messages: list) -> str:
    try:
        if not OPENROUTER_KEY:
            return "ERROR"

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": messages
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenRouter Log: {e}")
    return "ERROR"


def call_groq_api(prompt_text: str) -> str:
    try:
        if not GROQ_KEY or not Groq:
            return "ERROR"

        client = Groq(api_key=GROQ_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.5
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Log: {e}")
    return "ERROR"


def get_fallback_ai_response(messages: list, prompt_text: str = "") -> str:
    if not prompt_text:
        prompt_text = "\n\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])

    res = call_openrouter_api(messages)
    if res != "ERROR":
        return res

    res = call_groq_api(prompt_text)
    if res != "ERROR":
        return res

    return "AI Assistant is active. Please enter your query."


# AI STUDY CHAT
@app.post("/ai/study-chat")
async def study_chat(payload: ChatRequest):
    system_prompt = (
        "You are an expert AI Study Assistant. Provide clear, structured responses."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload.message}
    ]
    ai_res = get_fallback_ai_response(messages, prompt_text=payload.message)
    return {"response": ai_res}
