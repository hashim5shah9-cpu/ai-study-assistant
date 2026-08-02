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
try:
    from mangum import Mangum
except BaseException:
    Mangum = None


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

# Ensure api directory is in sys.path for database module lookup
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


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "online", "message": "Backend server is live and working!"}


# ====================================================
# API KEYS CONFIGURATION (LOAD FROM ENV)
# ====================================================
GROQ_KEY = os.getenv("GROQ_KEY", "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")      
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "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")  
GEMINI_KEY = os.getenv("GEMINI_KEY", "AQ.Ab8RN6K5igFNFB0ayrDT3fELaPbHUh0eOeZI75jx1-CG2f5AvA")

class ChatRequest(BaseModel):
    message: str
    email: str = "guest@gmail.com"


# =====================================================================
# ENGINE 1: DIRECT GOOGLE GEMINI
# =====================================================================
def call_direct_gemini_api(prompt_text: str, data_url: str = "") -> str:
    try:
        if not GEMINI_KEY or not genai:
            return "ERROR"
            
        client = genai.Client(api_key=GEMINI_KEY)
        
        if data_url.strip():
            if "," in data_url:
                raw_b64 = data_url.split(",")[1]
            else:
                raw_b64 = data_url

            image_bytes = base64.b64decode(raw_b64)
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
            contents_payload = [prompt_text, image_part]
        else:
            contents_payload = prompt_text

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents_payload
        )
        if response and response.text:
            return response.text
    except Exception as e:
        print(f"Direct Gemini Engine Connection Log: {e}")
    return "ERROR"


# =====================================================================
# ENGINE 2: OPENROUTER
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
        print(f"OpenRouter Connection Log: {e}")
    return "ERROR"


# =====================================================================
# ENGINE 3: GROQ
# =====================================================================
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
        print(f"Groq Connection Log: {e}")
    return "ERROR"


# =====================================================================
# ENGINE 4: FREE FALLBACK VISION ENGINE
# =====================================================================
def call_free_vision_fallback(data_url: str, prompt_text: str) -> str:
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ],
            "model": "openai"
        }
        res = requests.post("https://text.pollinations.ai/", json=payload, timeout=12)
        if res.status_code == 200 and res.text.strip():
            return res.text
    except Exception as e:
        print(f"Free Fallback Engine Log: {e}")
    return "ERROR"


# =====================================================================
# CORE INTEGRATED MULTI-FALLBACK ENGINE
# =====================================================================
def get_fallback_ai_response(messages: list, raw_b64_image: str = "", prompt_text: str = "") -> str:
    if not prompt_text:
        prompt_text = "\n\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])

    # 1. Primary Engine: Direct Google Gemini API
    res = call_direct_gemini_api(prompt_text=prompt_text, data_url=raw_b64_image)
    if res != "ERROR":
        return res

    # 2. Secondary Engine: OpenRouter
    res = call_openrouter_api(messages)
    if res != "ERROR":
        return res

    # 3. Tertiary Engine: Groq
    res = call_groq_api(prompt_text)
    if res != "ERROR":
        return res

    # 4. Quaternary Engine: Open Fallback Vision
    if raw_b64_image:
        res = call_free_vision_fallback(raw_b64_image, prompt_text)
        if res != "ERROR":
            return res

    return "Tamam AI Engines respond nahi kar rahe. Meharbani karke backend credentials check karein."


# AI STUDY CHAT
@app.post("/ai/study-chat")
async def study_chat(payload: ChatRequest):
    system_prompt = (
        "You are an expert, friendly AI Study Assistant. Provide highly structured, "
        "beautiful, and easy-to-read responses using clear formatting rules.\n"
        "Rules:\n"
        "1. Use '### Heading Name' for major topics or sub-sections.\n"
        "2. Use single asterisk bullets '* Keypoint: details' for bullet items.\n"
        "3. Use '**text**' to bold critical key terms.\n"
        "4. Always add a newline character between paragraphs and headings to avoid text crowding.\n"
        "Prioritize scannability and structural hierarchy."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload.message}
    ]
    
    ai_res = get_fallback_ai_response(messages, prompt_text=f"{system_prompt}\n\nUser Question: {payload.message}")
    
    db = get_db_connection()
    if db:
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (payload.email,))
            user_data = cursor.fetchone()
            
            user_id = 4 if not user_data else user_data['user_id']
                
            query = """
                INSERT INTO chat_history (user_id, prompt, response)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (user_id, payload.message, ai_res))
            db.commit() 
            cursor.close()
        except Exception as db_err:
            if db:
                try:
                    db.rollback()
                except Exception:
                    pass
        finally:
            try:
                db.close()
            except Exception:
                pass

    return {"response": ai_res}


# AI SUMMARIZE
@app.post("/ai/summarize")
async def summarize(file: UploadFile = File(...), email: str = Form("guest@gmail.com")):
    extracted_text = ""
    filename = file.filename.lower()
    
    try:
        file_bytes = await file.read()
        
        if filename.endswith('.txt'):
            extracted_text = file_bytes.decode("utf-8")
        elif filename.endswith('.pdf') and PdfReader:
            pdf_file = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                text = page.extract_text()
                if text: extracted_text += text + "\n"
        elif (filename.endswith('.ppt') or filename.endswith('.pptx')) and Presentation:
            ppt_file = io.BytesIO(file_bytes)
            prs = Presentation(ppt_file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        extracted_text += shape.text + "\n"
        else:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")
            
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="File text read nahi ho saka.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File reading error: {str(e)}")

    system_prompt = (
        "You are an expert academic summarizer. Summarize the provided text in simple words."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please summarize this text: {extracted_text}"}
    ]
    
    ai_res = get_fallback_ai_response(messages, prompt_text=f"{system_prompt}\n\nPlease summarize this text:\n{extracted_text}")
    return {"response": ai_res}


# Request Models for Auth
class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

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

handler = Mangum(app) if Mangum else app

