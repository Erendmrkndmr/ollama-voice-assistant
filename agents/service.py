import os, base64, tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "phi3:mini")
PERSONA_DIR = Path(os.getenv("PERSONA_DIR", "ollama/persona_prompts"))
ASSISTANT_LANG = os.getenv("ASSISTANT_LANG", "en")

PERSONAS = {
    "customer_support": PERSONA_DIR / "customer_support.txt",
    "devops_advisor": PERSONA_DIR / "devops_advisor.txt",
    "technical_coach": PERSONA_DIR / "technical_coach.txt",
}

class ChatRequest(BaseModel):
    persona: str = Field(examples=["devops_advisor"])
    directive: str = Field(default="Be concise and accurate.")
    message: str = Field(examples=["How do I roll back a bad deploy?"])
    model: str = Field(default=DEFAULT_MODEL)
    speak: bool = Field(default=False)

class ChatResponse(BaseModel):
    response: str
    audio_b64: str | None = None

app = FastAPI(title="Assistant Agent Service")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

def build_prompt(persona_file: Path, directive: str, user_input: str) -> str:
    base = persona_file.read_text(encoding="utf-8")
    lang_clause = f"Answer in {ASSISTANT_LANG.upper()}." if ASSISTANT_LANG else ""
    return f"""{base}

# Custom Directive:
{directive}
{lang_clause}

# Conversation:
User: {user_input}
Assistant:"""

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    key = req.persona.lower().replace(" ", "_")
    pfile = PERSONAS.get(key)
    if not pfile or not pfile.exists():
        raise HTTPException(status_code=400, detail=f"Persona not found: {req.persona}")

    prompt = build_prompt(pfile, req.directive, req.message)
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": req.model, "prompt": prompt, "stream": False},
            timeout=120
        )
        r.raise_for_status()
        data = r.json()
        text = (data.get("response") or "").strip()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

    audio_b64 = None
    if req.speak and os.getenv("ASSISTANT_TTS", "False").lower() == "true":
        try:
            import pyttsx3
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            eng = pyttsx3.init()
            eng.save_to_file(text, tmp.name)
            eng.runAndWait()
            with open(tmp.name, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("ascii")
            os.unlink(tmp.name)
        except Exception:
            audio_b64 = None  # TTS hata verse de metin dön

    return ChatResponse(response=text, audio_b64=audio_b64)
