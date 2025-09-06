# agents/agent_runner.py
import sys
from pathlib import Path
import requests

OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "phi3:mini"

def generate(model: str, prompt: str, stream=False, timeout=60) -> str:
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": stream}
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "").strip()

def build_prompt(persona_file: Path, directive: str, user_input: str) -> str:
    base = persona_file.read_text(encoding="utf-8")
    return f"""{base}

# Custom Directive:
{directive}

# Conversation:
User: {user_input}
Assistant:"""

if __name__ == "__main__":
    persona_map = {
        "customer support": Path("ollama/persona_prompts/customer_support.txt"),
        "devops advisor": Path("ollama/persona_prompts/devops_advisor.txt"),
        "technical coach": Path("ollama/persona_prompts/technical_coach.txt"),
    }
    persona = (sys.argv[1] if len(sys.argv) > 1 else "devops advisor").lower()
    directive = sys.argv[2] if len(sys.argv) > 2 else "Be concise and accurate."
    user_msg = sys.argv[3] if len(sys.argv) > 3 else "Say hello in one short sentence."

    pfile = persona_map.get(persona)
    if not pfile or not pfile.exists():
        raise FileNotFoundError(f"Persona file not found for: {persona}")

    prompt = build_prompt(pfile, directive, user_msg)
    print(generate(DEFAULT_MODEL, prompt, stream=False))
