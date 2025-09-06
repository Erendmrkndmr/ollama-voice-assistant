# scripts/voice_chat.py
import os
from pathlib import Path
import requests
from voice.whisper import record_until_silence, transcribe, STT_LANG
from dotenv import load_dotenv
from os import getenv

load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"))


# ---- Config (env-overridable)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("LLM_MODEL", "phi3:mini")

PERSONA_DIR = Path(os.getenv("PERSONA_DIR", "ollama/persona_prompts"))
PERSONA = os.getenv("PERSONA_TYPE", "devops_advisor").lower().replace(" ", "_")
DIRECTIVE = os.getenv("CUSTOM_DIRECTIVE", "Be concise and accurate.")
ASSISTANT_LANG = os.getenv("ASSISTANT_LANG", "tr")


GEN_OPTIONS = {
    "num_predict": int(os.getenv("NUM_PREDICT", "64")),
    "temperature": float(os.getenv("TEMP", "0.2")),
    "top_p": float(os.getenv("TOP_P", "0.9")),
    "repeat_penalty": float(os.getenv("REPEAT_PENALTY", "1.1")),
    "seed": int(os.getenv("SEED", "42")),
}

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

def generate(prompt: str) -> str:
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False, "options": GEN_OPTIONS},
        timeout=120
    )
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()

if __name__ == "__main__":
    persona_file = PERSONA_DIR / f"{PERSONA}.txt"
    if not persona_file.exists():
        raise FileNotFoundError(f"Persona not found: {persona_file}")

    print("[🎧] Voice chat loop. Speak; pause to send. Ctrl+C to exit.")
    while True:
        pcm = record_until_silence()
        if pcm.size == 0:
            continue
        user_text = transcribe(pcm, model_size="base", language=STT_LANG or "tr")
        if not user_text:
            print("[…] No speech recognized. Try again.")
            continue
        print(f"[User ]: {user_text}")

        prompt = build_prompt(persona_file, DIRECTIVE, user_text)
        reply = generate(prompt)
        print(f"[Agent]: {reply}")

        if os.getenv("ASSISTANT_TTS", "False").lower() == "true":
            try:
                from voice.tts_pyttsx3 import speak
                speak(reply)
            except Exception as e:
                print(f"[TTS warn] {e}")

