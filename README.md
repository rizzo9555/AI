# AI Services Reinstall Guide

Step-by-step guide to reinstall all AI-related services on a fresh Ubuntu setup.

## Hardware Reference

| Component | Spec |
|---|---|
| CPU | AMD Ryzen 9 5950X |
| RAM | 32GB 3600MHz |
| GPU | GeForce RTX 4080 SUPER 16GB |
| Motherboard | Aorus X570 Elite |
| OS Drive | Samsung SSD 990 PRO 2TB (500GB Ubuntu / 1.3TB Windows / 200GB Bazzite) |
| Games Drive | Samsung SSD 970 EVO 500GB |

> This guide targets the **Ubuntu** partition (500GB).

---

## 1. NVIDIA Driver & CUDA Setup

Install the latest recommended NVIDIA driver:

```bash
sudo apt update
sudo ubuntu-drivers autoinstall
sudo reboot
```

Verify the driver installation:

```bash
nvidia-smi
```

Install the CUDA Toolkit (latest version, via the official NVIDIA repository):

```bash
# Follow the official instructions for your Ubuntu version:
# https://developer.nvidia.com/cuda-downloads
```

Verify CUDA:

```bash
nvcc --version
```

---

## 2. Ollama Installation

Install Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verify the service is running:

```bash
systemctl status ollama
```

### 2.1 Model Storage Location

Models downloaded via `ollama pull` are stored at:

```
/usr/share/ollama/.ollama/models
```

### 2.2 Reinstalling Models

Pull each model back down:

```bash
ollama pull qwen3-coder:30b
ollama pull qwen3.8:27b
ollama pull qwen2.5-coder:14b
ollama pull gpt-oss:20b
ollama pull deepseek-r1:14b
ollama pull gemma4:26b
ollama pull gemma4:12b
ollama pull qwen3:14b
```

Verify installed models:

```bash
ollama list
```

---

## 3. Open WebUI (Docker)

> **Why Ollama stays native and isn't dockerized:** with a dedicated NVIDIA GPU, native Ollama uses the system driver directly with zero extra config. Dockerizing it would require installing and maintaining the NVIDIA Container Toolkit just for GPU passthrough, with no real benefit on a single-machine setup. Open WebUI itself doesn't touch the GPU (it's just the web interface), so only it needs to be containerized — the NVIDIA Container Toolkit step is skipped entirely.

### 3.1 Install Docker

Using Docker's official install script (simpler than the manual apt-repository method, works across distros):

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

Allow running Docker without `sudo` (optional but recommended):

```bash
sudo usermod -aG docker $USER
```

> Log out and back in (or restart the terminal/session) for the group change to take effect.

Confirm the Docker service is running and enabled to start on boot:

```bash
sudo systemctl status docker
sudo systemctl is-enabled docker   # should say "enabled"; if not: sudo systemctl enable docker
```

Verify Docker:

```bash
docker run hello-world
```

### 3.2 Run Open WebUI

Since Ollama runs natively (not in Docker), Open WebUI is run with `--network=host` so the container shares the host's network stack and can reach Ollama directly at `127.0.0.1:11434` — no port mapping or `host.docker.internal` needed on Linux.

```bash
docker run -d \
  --name open-webui \
  --network=host \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

Access the interface at:

```
http://localhost:8080
```

> Note: `--network=host` is Linux-specific and is why the port is 8080 directly (no `-p` mapping) rather than remapped to 3000 as on Mac/Windows setups.

### 3.3 Verify

```bash
docker ps
docker logs open-webui
```

### 3.4 LAN Access (other devices at home)

Find the machine's local IP:

```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

From another device on the same network, open `http://<LOCAL_IP>:8080`. If it doesn't connect, check the firewall:

```bash
sudo ufw status
sudo ufw allow 8080/tcp   # if ufw is active and the port isn't allowed
```

> Consider setting a DHCP reservation for this machine on the router so the local IP doesn't change on reboot.

### 3.5 Remote Access (internet)

Not yet configured. Preferred approach when needed: a VPN (e.g. Tailscale) rather than a public reverse proxy — no ports exposed to the internet, simplest to set up for personal use.

### 3.6 First Login & Users

The first account created at `http://localhost:8080` becomes the admin automatically. Additional users (e.g. family members) are added manually via *Admin Panel → Users → Add User*. The "email" field is required as a login identifier but doesn't need to be a real, working address (e.g. `name@family.local` works fine — nothing is sent to it).

---

## 4. Post-Install Checklist

- [ ] `nvidia-smi` shows the RTX 4080 SUPER correctly
- [ ] `ollama list` shows all 8 models
- [ ] `sudo systemctl is-enabled docker` returns `enabled`
- [ ] Open WebUI loads at `http://localhost:8080`
- [ ] Open WebUI can see and query the Ollama models
- [ ] GPU usage confirmed during inference (`nvidia-smi` while running a prompt)
- [ ] Open WebUI reachable from another device via `http://<LOCAL_IP>:8080`
- [ ] Admin account created; additional family user accounts added

---

## 5. Mem0 — Agent Memory Layer (venv, Graph Memory)

Gives agents (starting with CrewAI) persistent memory: a vector store (Qdrant, embedded/local) for semantic recall plus a graph store (Neo4j) for entity/relationship memory. Runs as a Python library inside a dedicated venv — not the official Docker server bundle, since that bundle only supports OpenAI/Anthropic/Gemini out of the box (see Pending list below). Fully local via Ollama.

### 5.1 Create the venv and install Mem0

```bash
mkdir -p ~/Projects/AI/ai-agents/mem0 && cd ~/Projects/AI/ai-agents/mem0
python3 -m venv venv-mem0
source venv-mem0/bin/activate
pip install mem0ai ollama neo4j langchain-neo4j python-dotenv
```

> Note: as of `mem0ai` 2.2.0, the `[graph]` install extra was dropped — the `neo4j`/`langchain-neo4j` packages must be installed manually, as above. The `ollama` package (official Python client) is also required separately for the Ollama embedder to work.

### 5.2 Run Neo4j locally (Docker, with APOC plugin)

Graph Memory requires the **APOC** plugin enabled:

```bash
mkdir -p ~/Projects/AI/ai-agents/mem0/neo4j/data ~/Projects/AI/ai-agents/mem0/neo4j/plugins

docker run -d \
  --name neo4j-mem0 \
  -p 7474:7474 -p 7687:7687 \
  -v ~/Projects/AI/ai-agents/mem0/neo4j/data:/data \
  -v ~/Projects/AI/ai-agents/mem0/neo4j/plugins:/plugins \
  -e NEO4J_AUTH=neo4j/CHANGE_ME_ON_FIRST_BOOT \
  -e NEO4J_apoc_export_file_enabled=true \
  -e NEO4J_apoc_import_file_enabled=true \
  -e NEO4J_apoc_import_file_use__neo4j__config=true \
  -e NEO4JLABS_PLUGINS='["apoc"]' \
  --restart always \
  neo4j:latest
```

- Port `7474`: Neo4j Browser (`http://localhost:7474`)
- Port `7687`: Bolt protocol (used by Mem0 to connect)
- `NEO4J_AUTH` only sets the password on **first boot of an empty data volume**. To change the password later without losing data, log into the Browser and run: `ALTER CURRENT USER SET PASSWORD FROM 'old' TO 'new';`

### 5.3 Ollama models required

```bash
ollama pull nomic-embed-text
```

(Reuses an existing chat/reasoning model, e.g. `qwen3:14b`, for entity/fact extraction — no separate pull needed.)

### 5.4 Secrets — `.env`

Create `~/Projects/AI/ai-agents/mem0/.env` (gitignored — see Section 6):

```
NEO4J_PASSWORD=your_real_password_here
```

Keep a `.env.example` (no real value, safe to commit) alongside it:

```
NEO4J_PASSWORD=
```

### 5.5 `config.py`

```python
import os
from dotenv import load_dotenv
from mem0 import Memory

load_dotenv()

config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen3:14b",
            "ollama_base_url": "http://localhost:11434"
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434"
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_memories",
            "embedding_model_dims": 768,
            "path": "/home/guilherme/Projects/AI/ai-agents/mem0/qdrant_data"
        }
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": os.getenv("NEO4J_PASSWORD"),
            "database": "neo4j"
        }
    },
    "version": "v1.1"
}

memory = Memory.from_config(config_dict=config)
```

> `embedding_model_dims: 768` matches `nomic-embed-text`'s output size — Mem0's Qdrant default (1536) is sized for OpenAI embeddings and must be overridden or `add`/`search` will fail with a dimension mismatch.

### 5.6 Test

```python
# test_mem0.py
from config import memory

conversation = [
    {"role": "user", "content": "Uso Ollama local com uma RTX 4080 Super de 16GB."},
    {"role": "assistant", "content": "Entendido, vou lembrar disso."}
]

memory.add(conversation, user_id="rizzo")

results = memory.search(
    "Qual GPU eu uso?",
    filters={"user_id": "rizzo"},
    limit=3
)
for hit in results["results"]:
    print(hit["memory"])
```

```bash
python test_mem0.py
```

Verify the graph side by opening `http://localhost:7474` and running `MATCH (n) RETURN n LIMIT 25;` — connected nodes confirm Graph Memory is writing correctly.

> Note: `search()` requires `user_id` inside `filters={}` — passing it as a top-level kwarg (as `add()` still accepts) raises a `ValueError` on current versions.

---

## 6. Git — `~/Projects/AI` repo

`~/Projects/AI` is a git repository. `.gitignore` at its root should include:

```gitignore
# Python virtual environments
**/venv*/
__pycache__/
*.pyc

# Local databases (data, not source)
ai-agents/mem0/neo4j/data/
ai-agents/mem0/neo4j/plugins/
ai-agents/mem0/qdrant_data/

# Secrets
.env
```

---

## Pending / To Investigate

- [ ] **"Coding" agent (remote terminal assistant)** — e.g. Letta's App Server / Letta Code (shell + filesystem access, Telegram/Slack integration). Confirmed free/local capable (no paid plan required for self-hosted runtime). Not yet installed — placeholder for future steps once evaluated.
- [ ] **CrewAI — RAG/context management** — no native integration available; must be manually delegated to a dedicated tool/agent role within the crew.
- [ ] **Mem0 — Docker server option (deferred)** — official Docker bundle only supports OpenAI/Anthropic/Gemini out of the box (no native Ollama support). Would require modifying `server/main.py` and rebuilding the image to add Ollama — deferred for now in favor of the venv/library setup in Section 5; revisit if the dashboard/API becomes worth the maintenance overhead of a custom fork.
- [ ] **Mem0 — optional extras**: `spaCy` (`pip install "mem0ai[nlp]"`) for more refined entity extraction; `fastembed` (`pip install "mem0ai[extras]"`) to enable BM25 keyword search alongside semantic search.
- [ ] **CrewAI ↔ Mem0 integration** — wire up `config.py`'s `memory` object as a tool/memory source for a CrewAI agent (next step).

## Notes

- This guide assumes a fresh Ubuntu install on the 500GB partition of the Samsung 990 PRO 2TB.
- Update model list in Section 2.2 as new models are added/removed.
- Update Section 3 if additional Docker containers (vector databases, n8n, etc.) are introduced later.
- Ollama is intentionally kept native, not dockerized — see the note at the top of Section 3.
- Section 3.5 (remote access) is a placeholder until that setup is actually done.
