FROM python:3.11-slim

WORKDIR /app
COPY requirements-core.txt /app/
RUN pip install --no-cache-dir -r requirements-core.txt

# Uygulama dosyaları
COPY agents /app/agents
COPY ollama/persona_prompts /app/ollama/persona_prompts
COPY .env.example /app/.env.example

ENV OLLAMA_URL=http://ollama:11434
ENV LLM_MODEL=phi3:mini
ENV PERSONA_DIR=/app/ollama/persona_prompts
ENV ASSISTANT_LANG=en
ENV ASSISTANT_TTS=False

EXPOSE 8080
CMD ["uvicorn", "agents.service:app", "--host", "0.0.0.0", "--port", "8080"]
