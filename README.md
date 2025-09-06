# Ollama Voice Assistant 🚀

Ollama-powered, **persona-configurable** assistant.\
Supports both text and voice interaction, fully automated with Jenkins
pipeline for **build & deploy**.

## ✨ Features

-   ✅ **Ollama-powered LLM** (local models)
-   ✅ **Persona selection** (Customer Support, DevOps Advisor,
    Technical Coach)
-   ✅ **Custom directive support** (control response style)
-   ✅ **Web UI** (modern, user-friendly, voice-to-text &
    text-to-speech)
-   ✅ **Docker Compose** for easy service setup
-   ✅ **Jenkins Pipeline** (parameterized build, model pull, smoke
    test)
-   ✅ **Optional TTS** (pyttsx3 or external services)

------------------------------------------------------------------------

## 📂 Project Structure

``` bash
.
├── agents/              # FastAPI agent backend
│   └── service.py
├── ollama/              # Persona prompt files
│   └── persona_prompts/
├── voice/               # Voice models (optional TTS/STT)
├── docker/              # docker-compose.yml, agent.Dockerfile
├── jenkins/             # Jenkinsfile (pipeline)
├── agents/ui/           # Web frontend (index.html, JS, CSS)
├── requirements.txt
├── .env.example         # Example environment variables
└── README.md
```

------------------------------------------------------------------------

## ⚙️ Setup

### 1. Prerequisites

-   Docker & Docker Compose
-   Jenkins (Docker or host-based)
-   (Optional) Python 3.11+ for local testing

### 2. Environment File

Copy `.env.example`:

``` bash
cp .env.example .env
```

Key variables:

``` env
OLLAMA_URL=http://ollama:11434
LLM_MODEL=phi3:mini
NUM_PREDICT=64
TEMP=0.2
TOP_P=0.9
REPEAT_PENALTY=1.1
```

### 3. Start Services

### Option A: With Jenkins (recommended)
Spin up everything including Jenkins:
```bash
docker compose -f docker/docker-compose.jenkins.yml up -d --build
```

Jenkins will be available at: [http://localhost:8081](http://localhost:8081)

- Login with admin credentials configured in `casc.yaml`.
- Use **"Build with Parameters"** → select persona, model, directive, etc.
- Pipeline will:
  1. Pull repo  
  2. Launch Ollama  
  3. Build & run Agent  
  4. Validate `/healthz` and `/readyz`  
  5. Expose chat service

### Option B: Locally (without Jenkins)
Run only Ollama + Agent + UI:
```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Services:
- **Ollama API** → `http://localhost:11434`
- **Agent API** → `http://localhost:8080`
- **Web UI** → `http://localhost:8080/ui/`

---

## Stopping Services
```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.jenkins.yml down
```

---



### 4. Health Check

``` bash
curl -s http://localhost:8080/healthz
# {"status":"ok"}

curl -s http://localhost:8080/readyz
# {"status":"ready"}
```

------------------------------------------------------------------------

## 💻 Usage

### Web UI

-   Open in browser: <http://localhost:8080/ui/>\
-   Select persona → type or speak → view assistant response.

### API Example

``` bash
curl -s http://localhost:8080/chat   -H 'Content-Type: application/json'   -d '{
    "persona":"DevOps Advisor",
    "directive":"Be concise and accurate.",
    "message":"How do I roll back a bad deploy?",
    "model":"phi3:mini",
    "speak": false
  }'
```

Response:

``` json
{
  "response": "Use your deployment tool’s rollback feature to revert...",
  "audio_b64": null
}
```

------------------------------------------------------------------------

## 🔄 Jenkins Pipeline

Pipeline **Acme-Assistant-Deploy** job runs as follows: 1. Repo checkout
(`dev` branch). 2. `.env` file generation. 3. **Ollama** container
starts and pulls model. 4. **Agent** container builds & starts. 5.
Health checks run (`/healthz`, `/readyz`). 6. Smoke test: `/chat`
endpoint tested. 7. Logs stored in `logs/agent_smoke.json`.

Pipeline parameters: - **LLM_MODEL** → (e.g. `phi3:mini`, `mistral`,
`llama3:8b`) - **PERSONA_TYPE** → Customer Support, DevOps Advisor,
etc. - **CUSTOM_DIRECTIVE** → e.g. "Be concise", "Explain step by step"

------------------------------------------------------------------------

## 🧪 Test Scenarios

### 1. Healthz & Readyz

``` bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
```

### 2. Basic Chat

``` bash
curl -s http://localhost:8080/chat   -H 'Content-Type: application/json'   -d '{"persona":"Customer Support","directive":"Answer politely","message":"Hello!","model":"phi3:mini","speak":false}'
```

### 3. TTS (speak=true)
1. Open the UI: [http://localhost:8080/ui/](http://localhost:8080/ui/)  
   - Select persona, directive, and model.
   - Type or use mic 🎤 to chat.
   - Optionally enable "Speak replies" if TTS is active.

------------------------------------------------------------------------

## 🛑 Stop All Services

``` bash
docker stop $(docker ps -q)
```

------------------------------------------------------------------------

## 📌 Progress So Far

-   Dockerized **Ollama + Agent + Jenkins** pipeline setup.
-   Persona files managed as plain text prompts.
-   Web UI modernized with mic & text input.
-   Inference parameters configurable via `.env`.
-   Jenkins pipeline handles pull, deploy & smoke tests.

------------------------------------------------------------------------