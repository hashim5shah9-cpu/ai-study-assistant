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

app = FastAPI()

# 1. CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory persistent user store for fast serverless execution
USERS_STORE = {}

def safe_get_db():
    try:
        api_dir = os.path.dirname(os.path.abspath(__file__))
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        import database
        return database.get_db_connection()
    except BaseException:
        return None


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

class QuizRequest(BaseModel):
    topic: str
    email: str = "guest@gmail.com"

class CodeExplanationRequest(BaseModel):
    code: str
    language: str = "auto"
    target_language: str = "Roman Urdu/Hindi"
    email: str = "guest@gmail.com"

class ImageExplanationRequest(BaseModel):
    image_base64: str
    target_language: str = "Roman Urdu/Hindi"
    custom_prompt: str = ""
    email: str = "guest@gmail.com"


# SIGNUP ENDPOINT
@app.post("/auth/signup")
async def signup(payload: SignupRequest):
    email = payload.email.lower().strip()
    if email in USERS_STORE:
        raise HTTPException(status_code=400, detail="Email pehle se registered hai!")
    
    USERS_STORE[email] = {
        "username": payload.username,
        "email": email,
        "password": payload.password
    }
    
    db = safe_get_db()
    if db:
        try:
            cursor = db.cursor(dictionary=True) if hasattr(db, 'cursor') else None
            if cursor:
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                if not cursor.fetchone():
                    query = "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)"
                    cursor.execute(query, (payload.username, email, payload.password))
                    db.commit()
                cursor.close()
        except Exception:
            pass
        finally:
            try:
                db.close()
            except Exception:
                pass

    return {"message": "Account successfully created!"}


# LOGIN ENDPOINT
@app.post("/auth/login")
async def login(payload: LoginRequest):
    email = payload.email.lower().strip()
    user = USERS_STORE.get(email)
    
    if not user:
        db = safe_get_db()
        if db:
            try:
                cursor = db.cursor(dictionary=True) if hasattr(db, 'cursor') else None
                if cursor:
                    query = "SELECT user_id, username, email, password_hash FROM users WHERE email = %s"
                    cursor.execute(query, (email,))
                    db_user = cursor.fetchone()
                    cursor.close()
                    if db_user and (db_user.get('password_hash') == payload.password or db_user.get('password') == payload.password):
                        user = {
                            "username": db_user.get('username', 'User'),
                            "email": email,
                            "password": payload.password
                        }
                        USERS_STORE[email] = user
            except Exception:
                pass
            finally:
                try:
                    db.close()
                except Exception:
                    pass

    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="Ghalat email ya password!")
        
    return {
        "token": "fake-jwt-token",
        "email": user['email'],
        "username": user['username']
    }


# =====================================================================
# AI ENGINES WITH MULTI-FALLBACK
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
            timeout=12
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenRouter Log: {e}")
    return "ERROR"


def call_groq_api(prompt_text: str) -> str:
    try:
        if not GROQ_KEY:
            return "ERROR"

        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt_text}]
            },
            timeout=12
        )
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Groq Log: {e}")
    return "ERROR"


def call_pollinations_vision_api(raw_b64: str, prompt_text: str) -> str:
    try:
        data_url = f"data:image/jpeg;base64,{raw_b64}" if not raw_b64.startswith("data:") else raw_b64
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
        res = requests.post("https://text.pollinations.ai/", json=payload, timeout=15)
        if res.status_code == 200 and res.text.strip():
            return res.text
    except Exception as e:
        print(f"Pollinations Vision Log: {e}")
    return "ERROR"


def get_fallback_ai_response(messages: list, raw_b64_image: str = "", prompt_text: str = "") -> str:
    if not prompt_text:
        prompt_text = "\n\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])

    # 1. Primary Engine: OpenRouter (Gemini 2.5 Flash)
    res = call_openrouter_api(messages)
    if res != "ERROR":
        return res

    # 2. Secondary Engine: Groq REST API (Llama 3.3 70b)
    res = call_groq_api(prompt_text)
    if res != "ERROR":
        return res

    # 3. Vision Fallback if Image is present
    if raw_b64_image:
        res = call_pollinations_vision_api(raw_b64_image, prompt_text)
        if res != "ERROR":
            return res

    return "AI Assistant is active. Please enter your query."


# 1. AI STUDY CHAT
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
    return {"response": ai_res}


# 2. AI TEXT SUMMARIZER
@app.post("/ai/summarize")
async def summarize(file: UploadFile = File(...), email: str = Form("guest@gmail.com")):
    extracted_text = ""
    filename = file.filename.lower()
    
    try:
        file_bytes = await file.read()
        extracted_text = file_bytes.decode("utf-8", errors="ignore")
        if not extracted_text.strip():
            extracted_text = f"Uploaded File: {file.filename}"
    except Exception:
        extracted_text = f"Uploaded File: {file.filename}"

    system_prompt = (
        "You are an expert academic summarizer. Summarize the provided text in simple, clear words."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please summarize this text: {extracted_text}"}
    ]
    
    ai_res = get_fallback_ai_response(messages, prompt_text=f"{system_prompt}\n\nPlease summarize this text:\n{extracted_text}")
    return {"response": ai_res}


# 3. AI QUIZ GENERATOR
@app.post("/ai/generate-quiz")
async def generate_quiz(payload: QuizRequest):
    system_prompt = (
        "You are an expert quiz master. Generate a quiz with exactly 5 multiple choice questions "
        "about the requested topic. Your entire response must be a single valid JSON list, "
        "with absolutely no markdown formatting, no code blocks (like ```json), and no extra text. "
        "Each object in the list must match this exact format: "
        '{"question": "Question text here", "a": "Option A", "b": "Option B", "c": "Option C", "d": "Option D", "answer": "a"}'
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate a quiz about: {payload.topic}"}
    ]
    
    full_prompt = f"{system_prompt}\n\nGenerate a quiz about: {payload.topic}"
    ai_raw_res = get_fallback_ai_response(messages, prompt_text=full_prompt)
    
    clean_json_str = re.sub(r"```json|```", "", ai_raw_res).strip()
    
    try:
        questions_list = json.loads(clean_json_str)
    except Exception:
        questions_list = [
            {
                "question": f"What is a core fundamental concept in {payload.topic}?",
                "a": "Basic Component Architecture",
                "b": "Secondary Data Stream",
                "c": "Null Execution Point",
                "d": "Random Access Buffer",
                "answer": "a"
            },
            {
                "question": f"Which principle applies directly to {payload.topic}?",
                "a": "Data Encapsulation & Logic Processing",
                "b": "Static Array Termination",
                "c": "Manual Register Allocation",
                "d": "Asynchronous Memory Flush",
                "answer": "a"
            }
        ]

    return {"quiz_id": 1, "questions": questions_list}


# 4. MULTI-UPLOAD DOCUMENT EXPLAINER
@app.post("/api/multi-upload-explain")
async def multi_upload_explain(
    file: UploadFile = File(...), 
    email: str = Form("guest@gmail.com")
):
    system_prompt = (
        "You are an advanced AI Academic Assistant. Analyze the provided document content and explain it in detail."
    )
    extracted_text = ""
    try:
        file_bytes = await file.read()
        extracted_text = file_bytes.decode("utf-8", errors="ignore")
        if not extracted_text.strip():
            extracted_text = f"Document File: {file.filename}"
    except Exception:
        extracted_text = f"Document content for {file.filename}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Explain this document text:\n{extracted_text}"}
    ]
    
    ai_explanation = get_fallback_ai_response(messages, prompt_text=f"{system_prompt}\n\nExplain:\n{extracted_text}")
    return {"explanation": ai_explanation}


# 5. CODE EXPLAINER ENDPOINT
@app.post("/api/explain-code")
async def explain_code(data: CodeExplanationRequest):
    if not data.code.strip():
        raise HTTPException(status_code=400, detail="Code content cannot be empty.")

    system_prompt = (
        f"You are a World-Class Computer Science Professor. Explain the following source code in target language ({data.target_language}).\n"
        "Structure:\n"
        "### 🎯 Purpose & Overview\n"
        "### 🔬 Line-by-Line Breakdown\n"
        "### 💡 Practical Analogy\n"
        "### ⚠️ Best Practices"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Programming Language: {data.language}\nCode:\n{data.code}"}
    ]
    
    ai_explanation = get_fallback_ai_response(messages, prompt_text=f"{system_prompt}\n\nCode:\n{data.code}")
    return {"explanation": ai_explanation}


# 6. IMAGE TO TEXT / EXPLAIN IMAGE ENDPOINT
@app.post("/api/explain-image")
async def explain_image(data: ImageExplanationRequest):
    if not data.image_base64.strip():
        raise HTTPException(status_code=400, detail="Image content cannot be empty.")

    system_prompt = (
        f"You are an Expert Multimodal Vision Specialist. Explain the provided image/diagram in detail in ({data.target_language})."
    )

    raw_b64 = data.image_base64
    user_text = data.custom_prompt.strip() if data.custom_prompt.strip() else "Please explain this image/diagram."
    full_prompt = f"{system_prompt}\n\n{user_text}"

    ai_explanation = get_fallback_ai_response([], raw_b64_image=raw_b64, prompt_text=full_prompt)
    return {"explanation": ai_explanation}
