Quick Start
-----------
cp .env.example .env
# set LLM_MODEL, ASSISTANT_LANG, etc.

docker compose -f docker/docker-compose.yml up -d
docker exec ollama ollama pull phi3:mini

# local STT test (optional)
pip install -r requirements-core.txt -r requirements-voice.txt
python -m voice.whisper

# voice chat CLI (optional)
python -m scripts.voice_chat

# HTTP agent
curl -s http://localhost:8080/readyz
curl -s http://localhost:8080/chat -H 'Content-Type: application/json' \
  -d '{"persona":"Customer Support","directive":"Be concise.","message":"Hello!"}'
