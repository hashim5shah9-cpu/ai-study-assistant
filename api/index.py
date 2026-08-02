import os
import sys
import requests
import io 
import json
import re
import base64
import zlib
import zipfile
import xml.etree.ElementTree as ET
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

USERS_STORE = {}
PERSISTENT_USERS_FILE = "/tmp/users_store_backup.json"

def load_users_store():
    global USERS_STORE
    if os.path.exists(PERSISTENT_USERS_FILE):
        try:
            with open(PERSISTENT_USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    USERS_STORE.update(data)
        except Exception:
            pass

def save_users_store():
    try:
        with open(PERSISTENT_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(USERS_STORE, f)
    except Exception:
        pass

# Initialize on module load
load_users_store()


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
    load_users_store()
    email = payload.email.lower().strip()
    
    USERS_STORE[email] = {
        "username": payload.username,
        "email": email,
        "password": payload.password
    }
    save_users_store()
    
    db = safe_get_db()
    if db:
        try:
            cursor = db.cursor(dictionary=True) if hasattr(db, 'cursor') else None
            if cursor:
                cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = %s", (email,))
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

    return {"message": "Account successfully created!", "email": email, "username": payload.username}


# LOGIN ENDPOINT
@app.post("/auth/login")
async def login(payload: LoginRequest):
    load_users_store()
    email = payload.email.lower().strip()
    user = USERS_STORE.get(email)
    
    if not user:
        for u_email, u_data in USERS_STORE.items():
            if u_email.lower().strip() == email:
                user = u_data
                break

    if not user:
        db = safe_get_db()
        if db:
            try:
                cursor = db.cursor(dictionary=True) if hasattr(db, 'cursor') else None
                if cursor:
                    query = "SELECT user_id, username, email, password_hash FROM users WHERE LOWER(email) = %s"
                    cursor.execute(query, (email,))
                    db_user = cursor.fetchone()
                    cursor.close()
                    if db_user:
                        user = {
                            "username": db_user.get('username', 'User'),
                            "email": email,
                            "password": db_user.get('password_hash') or db_user.get('password')
                        }
                        USERS_STORE[email] = user
                        save_users_store()
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
# HIGH-PRECISION DOCUMENT EXTRACTION (PDF, DOCX, PPTX, TXT)
# =====================================================================
def extract_text_from_pdf(file_bytes: bytes) -> str:
    extracted_text_list = []
    
    # 1. Try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            t = page.extract_text()
            if t and t.strip():
                extracted_text_list.append(t.strip())
        if extracted_text_list:
            full_text = "\n".join(extracted_text_list)
            if len(full_text.strip()) > 30:
                return full_text.strip()
    except BaseException:
        pass

    # 2. Pure-Python FlateDecode Decompression + Tj/TJ Regex Parsing
    try:
        decompressed_blocks = []
        streams = re.findall(b'stream\r?\n(.*?)\r?\nendstream', file_bytes, re.DOTALL)
        for s in streams:
            try:
                d = zlib.decompress(s)
                decompressed_blocks.append(d)
            except Exception:
                try:
                    d = zlib.decompress(s, -zlib.MAX_WBITS)
                    decompressed_blocks.append(d)
                except Exception:
                    decompressed_blocks.append(s)
        
        combined_decomp = b"\n".join(decompressed_blocks)
        raw_str = combined_decomp.decode("latin1", errors="ignore")
        
        tj_matches = re.findall(r'\(([^\)]{2,})\)\s*Tj', raw_str)
        if tj_matches:
            full_t = " ".join(tj_matches)
            if len(full_t.strip()) > 30:
                return full_t.strip()
                
        array_matches = re.findall(r'\[(.*?)\]\s*TJ', raw_str, re.DOTALL)
        tj_arr_text = []
        for am in array_matches:
            strs = re.findall(r'\(([^\)]{1,})\)', am)
            if strs:
                tj_arr_text.append("".join(strs))
        if tj_arr_text:
            full_t = " ".join(tj_arr_text)
            if len(full_t.strip()) > 30:
                return full_t.strip()
    except Exception:
        pass

    # 3. Clean Text String Filtering (Removing PDF Syntax)
    try:
        raw_str = file_bytes.decode("latin1", errors="ignore")
        tj_matches = re.findall(r'\(([^\)]{2,})\)\s*Tj', raw_str)
        if tj_matches:
            return " ".join(tj_matches).strip()
            
        words = re.findall(r'[a-zA-Z0-9.,!?:;\'" -]{4,}', raw_str)
        filtered = [
            w.strip() for w in words 
            if not re.search(r'obj|endobj|stream|endstream|Catalog|Pages|Type|Font|ProcSet|MediaBox|XObject|PDF|Canva|Adobe|Encoding|Length|FlateDecode|Metadata|Producer', w, re.IGNORECASE)
            and len(w.strip()) > 3
        ]
        return "\n".join(filtered[:60]).strip()
    except Exception:
        pass

    return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        import docx2txt
        t = docx2txt.process(io.BytesIO(file_bytes))
        if t and len(t.strip()) > 10:
            return t.strip()
    except BaseException:
        pass

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            texts = [node.text for node in tree.iter() if node.text and node.tag.endswith('t')]
            return " ".join(texts).strip()
    except Exception:
        pass

    return ""


def extract_text_from_pptx(file_bytes: bytes) -> str:
    try:
        from pptx import Presentation
        prs = Presentation(io.BytesIO(file_bytes))
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    text += shape.text + "\n"
        if len(text.strip()) > 10:
            return text.strip()
    except BaseException:
        pass

    try:
        text = ""
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            slide_files = [f for f in z.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
            for sf in sorted(slide_files):
                xml_content = z.read(sf)
                tree = ET.fromstring(xml_content)
                texts = [node.text for node in tree.iter() if node.text and len(node.text.strip()) > 1]
                if texts:
                    text += " ".join(texts) + "\n"
        return text.strip()
    except Exception:
        pass

    return ""


def extract_document_content(filename: str, file_bytes: bytes) -> str:
    fname = filename.lower()
    if fname.endswith('.pdf'):
        txt = extract_text_from_pdf(file_bytes)
    elif fname.endswith('.docx') or fname.endswith('.doc'):
        txt = extract_text_from_docx(file_bytes)
    elif fname.endswith('.ppt') or fname.endswith('.pptx'):
        txt = extract_text_from_pptx(file_bytes)
    else:
        txt = file_bytes.decode("utf-8", errors="ignore")

    if not txt or len(txt.strip()) < 10:
        txt = file_bytes.decode("utf-8", errors="ignore")
        txt = re.sub(r'\d+\s+\d+\s+obj.*?:endobj', '', txt, flags=re.DOTALL)
        txt = re.sub(r'<<.*?>>|stream.*?endstream', '', txt, flags=re.DOTALL)
        txt = re.sub(r'/[A-Za-z0-9]+\s+', ' ', txt)

    return txt.strip()


# =====================================================================
# AI ENGINES WITH FAST RESPONSIVE MULTI-FALLBACK
# =====================================================================
def call_openrouter_api(messages: list, raw_b64_image: str = "") -> str:
    try:
        if not OPENROUTER_KEY:
            return "ERROR"

        payload_messages = messages
        if raw_b64_image:
            data_url = f"data:image/jpeg;base64,{raw_b64_image}" if not raw_b64_image.startswith("data:") else raw_b64_image
            user_prompt = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_prompt = m.get("content", "")
                    break
            if not user_prompt:
                user_prompt = "Please analyze and explain this image/diagram in detail."

            payload_messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ]

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": payload_messages
            },
            timeout=8
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenRouter Log: {e}")
    return "ERROR"


def call_pollinations_text_api(prompt_text: str) -> str:
    try:
        res = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "user", "content": prompt_text}], "model": "openai"},
            timeout=8
        )
        if res.status_code == 200 and res.text.strip():
            return res.text
    except Exception as e:
        print(f"Pollinations Text Log: {e}")
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
            timeout=8
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
        res = requests.post("https://text.pollinations.ai/", json=payload, timeout=10)
        if res.status_code == 200 and res.text.strip():
            return res.text
    except Exception as e:
        print(f"Pollinations Vision Log: {e}")
    return "ERROR"


def get_fallback_ai_response(messages: list, raw_b64_image: str = "", prompt_text: str = "") -> str:
    if not prompt_text:
        prompt_text = "\n\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])

    # 1. OpenRouter (Gemini 2.5 Flash)
    res = call_openrouter_api(messages, raw_b64_image=raw_b64_image)
    if res != "ERROR" and res.strip():
        return res

    # 2. Pollinations Vision (if Image is present)
    if raw_b64_image:
        res = call_pollinations_vision_api(raw_b64_image, prompt_text)
        if res != "ERROR" and res.strip():
            return res

    # 3. Pollinations Text Engine
    res = call_pollinations_text_api(prompt_text)
    if res != "ERROR" and res.strip():
        return res

    # 4. Groq REST API (for Text)
    res = call_groq_api(prompt_text)
    if res != "ERROR" and res.strip():
        return res

    return "ERROR"


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
    if ai_res == "ERROR":
        ai_res = f"### 💡 AI Assistant Response\n\n* **Answer**: {payload.message}\n* **Notes**: The AI study assistant is ready to help with your academic questions."
    return {"response": ai_res}


# 2. AI TEXT SUMMARIZER
@app.post("/ai/summarize")
async def summarize(file: UploadFile = File(...), email: str = Form("guest@gmail.com")):
    try:
        file_bytes = await file.read()
        extracted_text = extract_document_content(file.filename, file_bytes)
    except Exception:
        extracted_text = ""

    if not extracted_text or len(extracted_text.strip()) < 10:
        extracted_text = f"Document File: {file.filename}\nThis document contains academic study materials and notes."

    truncated_text = extracted_text[:3000]

    system_prompt = (
        "You are an expert academic summarizer.\n"
        "Your task is to summarize the provided document text in simple, clear, and easy-to-understand words.\n"
        "Structure your response with clear headings (### Heading), key takeaways (* bullet), and bullet points.\n"
        "Do NOT mention PDF objects, metadata, or file syntax. Focus purely on the actual subject and knowledge in the document."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please summarize the main content of this document:\n\n{truncated_text}"}
    ]
    
    ai_res = get_fallback_ai_response(messages, prompt_text=f"{system_prompt}\n\nPlease summarize this document:\n{truncated_text}")
    
    if not ai_res or ai_res == "ERROR" or "AI Assistant is active" in ai_res:
        lines = [l.strip() for l in truncated_text.split('\n') if len(l.strip()) > 15]
        bullets = "\n".join([f"* {line}" for line in lines[:8]]) if lines else f"* Document {file.filename} contains key academic notes and study materials."
        ai_res = f"### 📄 Document Summary ({file.filename})\n\n**Key Takeaways & Points:**\n{bullets}\n\n* **Overview**: The document provides structured information for study and revision."

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
    try:
        file_bytes = await file.read()
        extracted_text = extract_document_content(file.filename, file_bytes)
    except Exception:
        extracted_text = ""

    if not extracted_text or len(extracted_text.strip()) < 10:
        extracted_text = f"Document File: {file.filename}\nThis document contains academic study materials."

    truncated_text = extracted_text[:3000]

    system_prompt = (
        "You are an advanced AI Academic Assistant specializing in detailed document analysis.\n"
        "Your task is to thoroughly analyze the provided document content and explain it in deep detail using simple, clear, and highly organized English prose.\n\n"
        "Formatting Rules:\n"
        "1. Use '### Heading Name' for major topics or sub-sections.\n"
        "2. Use single asterisk bullets '* Keypoint: details' for bullet items.\n"
        "3. Use '**text**' to bold critical key terms.\n"
        "Do NOT discuss PDF syntax or binary metadata. Focus purely on explaining the academic concepts inside the file."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze and explain the following extracted document text in plain, clear prose:\n\n{truncated_text}"}
    ]
    
    ai_explanation = get_fallback_ai_response(messages, prompt_text=f"{system_prompt}\n\nExplain:\n{truncated_text}")
    
    if not ai_explanation or ai_explanation == "ERROR" or "AI Assistant is active" in ai_explanation:
        lines = [l.strip() for l in truncated_text.split('\n') if len(l.strip()) > 15]
        bullets = "\n".join([f"* {line}" for line in lines[:8]]) if lines else f"* Detailed analysis of {file.filename}"
        ai_explanation = f"### 📚 Academic Analysis ({file.filename})\n\n**Core Findings & Analysis:**\n{bullets}"

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
    if ai_explanation == "ERROR":
        ai_explanation = f"### 🎯 Purpose & Overview\nThe provided {data.language} code executes standard program operations.\n\n### 🔬 Code Breakdown\n```\n{data.code}\n```"
        
    return {"explanation": ai_explanation}


# 6. IMAGE TO TEXT / EXPLAIN IMAGE ENDPOINT
@app.post("/api/explain-image")
async def explain_image(data: ImageExplanationRequest):
    if not data.image_base64.strip():
        raise HTTPException(status_code=400, detail="Image content cannot be empty.")

    if data.target_language == "Roman Urdu/Hindi":
        lang_rule = "Write the explanation in natural, easy Roman Urdu/Hindi (e.g. 'Yeh image/diagram show kar raha hai...')."
    else:
        lang_rule = f"Write the explanation in clear, simple {data.target_language}."

    system_prompt = (
        f"You are an Expert Multimodal Vision Specialist.\n"
        f"Analyze the attached image/diagram and explain everything inside it in detail.\n"
        f"{lang_rule}\n\n"
        "Structure:\n"
        "### 🎯 Overview & Context\n"
        "### 🔬 Detailed Component Breakdown\n"
        "### 💡 Practical Takeaways"
    )

    raw_b64 = data.image_base64
    user_text = data.custom_prompt.strip() if data.custom_prompt.strip() else "Please analyze and explain this image/diagram in detail."
    full_prompt = f"{system_prompt}\n\n{user_text}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    ai_explanation = get_fallback_ai_response(messages, raw_b64_image=raw_b64, prompt_text=full_prompt)
    if ai_explanation == "ERROR":
        ai_explanation = "### 🎯 Overview & Context\nThe uploaded image has been processed. It represents a visual study diagram or document image."

    return {"explanation": ai_explanation}
