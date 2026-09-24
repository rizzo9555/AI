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

> This guide targets the **Ubuntu** partition (500GB). Ubuntu 26.04 LTS ("resolute") ships only Python 3.14 by default — see Section 7.1 for why a second Python version is needed for CrewAI.

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

> **Important — Qdrant is running in local/embedded mode, not as a server.** Because `vector_store.config` uses `path` (not `host`/`port`), Qdrant has no separate process — it's a set of files on disk that Python opens directly. This means **only one process can have it open at a time**. Don't run a Mem0 standalone script and the CrewAI integration (Section 7) at the same time — one will fail to open the locked files.

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

> Note: `search()`/`get_all()` require `user_id` inside `filters={}` — passing it as a top-level kwarg (as `add()`/`delete_all()` still accept) raises a `ValueError` on current versions. This applies across `mem0ai` 2.x releases, at least down to `2.0.14`.

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

## 7. CrewAI ↔ Mem0 Integration (venv, manual tool)

Gives a CrewAI agent access to the Mem0 memory set up in Section 5, so it can recall facts/preferences across runs. **CrewAI has no built-in native support for a `"provider": "mem0"` memory backend** — confirmed by grepping the entire installed `crewai`/`crewai-core` source (version 1.15.22) for the string `"mem0"`: zero matches outside the `mem0` package itself. A `memory_config={"provider": "mem0", ...}` is silently ignored by this CrewAI version; it falls back to its own default (ChromaDB-based) memory, which then fails due to the `posthog`/`chromadb` version conflict noted in 7.4. Integration here is done manually instead, via a custom Tool.

### 7.1 Create the venv (separate from Mem0's) with Python 3.12

Ubuntu 26.04 ships only Python 3.14 by default, which lacks pre-built wheels for several CrewAI dependencies (e.g. `tiktoken`, which requires a Rust compiler to build from source on 3.14). Python 3.12 is used instead, installed via the Deadsnakes PPA:

```bash
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv
```

Then create the venv:

```bash
mkdir -p ~/Projects/AI/ai-agents/crewai && cd ~/Projects/AI/ai-agents/crewai
python3.12 -m venv venv
source venv/bin/activate
```

### 7.2 Install dependencies

Install in separate steps (installing everything in one `pip install` line can trigger a `resolution-too-deep` error — CrewAI's dependency tree, combined with `langchain-neo4j`, is too complex for pip to solve in one pass):

```bash
pip install --upgrade pip setuptools wheel
pip install crewai
pip install mem0ai==2.0.14
pip install python-dotenv
pip install neo4j
pip install langchain-neo4j
```

> `mem0ai` is pinned to `2.0.14` here for stability, though this pin turned out not to be the fix for the integration issue (see 7.4) — the `mem0` library itself works fine with any recent 2.x version, as long as `search()`/`get_all()` calls use `filters={"user_id": ...}` (see Section 5.6's note).

`mem0ai` also requires its own `.env` with `NEO4J_PASSWORD` — same value as Section 5.4, copy `~/Projects/AI/ai-agents/mem0/.env` or create a fresh one in the `crewai` folder.

### 7.3 The integration script

`~/Projects/AI/ai-agents/crewai/crewai_mem0_example.py` — a minimal working example. Key points:

- `memory=False` on the `Crew` — disables CrewAI's own (broken) default memory system.
- A custom `BaseTool` (`buscar_memoria`) that the agent calls explicitly to search Mem0 (`mem0_client.search(query, filters={"user_id": USER_ID}, limit=5)`).
- A `salvar_memoria()` helper function, called manually after each `crew.kickoff()`, that writes the turn to Mem0 (`mem0_client.add(..., user_id=USER_ID)`).
- The agent's LLM must be set **explicitly** to Ollama — `memory_config`/Mem0 setup has no effect on which LLM the *agent* itself uses to reason. Without this, CrewAI defaults to OpenAI and fails with `OPENAI_API_KEY is required`:

```python
from crewai import LLM
ollama_llm = LLM(model="ollama/qwen3:14b", base_url="http://localhost:11434")
# ...
agent = Agent(..., llm=ollama_llm, tools=[BuscarMemoriaTool()])
```

Full script kept alongside this README, in the same folder.

### 7.4 Troubleshooting notes (from setting this up)

- **`resolution-too-deep` on `pip install`**: install packages one at a time (Section 7.2), not all in one command.
- **`tiktoken` build fails needing a Rust compiler**: symptom of running on Python 3.14; switch to 3.12 (Section 7.1) rather than installing Rust.
- **Duplicated `(venv)` in the shell prompt** (e.g. `((venv) )`, `(venv) (venv)`): a known quirk when a venv is activated on top of another already-active one, or after a broken attempt to customize `PS1`. It's purely cosmetic (confirmed via `$VIRTUAL_ENV` and `which python3` — the correct interpreter is always used), but if it's distracting, the reliable fix is closing the terminal application entirely and opening a new one, then activating the venv once.
- **`OPENAI_API_KEY is required`**: the agent's `llm=` wasn't set explicitly — see Section 7.3.
- **`chromadb` requires `posthog<6.0.0`, but `mem0ai` installs `posthog>=7.x`**: a real, unresolved dependency conflict between CrewAI's default memory backend (ChromaDB) and Mem0. Not an issue for this integration since `memory=False` avoids ChromaDB entirely, but would need resolving if CrewAI's default memory is ever used alongside Mem0 in the same venv.
- **`memory_save_failed` warning with "empty scope stack"**: misleading — this came from CrewAI's default (ChromaDB) memory failing silently in the background (see `posthog` conflict above), not from Mem0. It disappeared once `memory=False` + the manual tool approach (Section 7.3) replaced the native `memory_config`.
- **Qdrant appears to not be running (`docker ps` doesn't show it, nothing on port 6333)**: expected — it's running in local/embedded mode (Section 5.6), not as a server.

---

## Pending / To Investigate

- [ ] **"Coding" agent (remote terminal assistant)** — e.g. Letta's App Server / Letta Code (shell + filesystem access, Telegram/Slack integration). Confirmed free/local capable (no paid plan required for self-hosted runtime). Not yet installed — placeholder for future steps once evaluated.
- [ ] **Mem0 — Docker server option (deferred)** — official Docker bundle only supports OpenAI/Anthropic/Gemini out of the box (no native Ollama support). Would require modifying `server/main.py` and rebuilding the image to add Ollama — deferred for now in favor of the venv/library setup in Section 5; revisit if the dashboard/API becomes worth the maintenance overhead of a custom fork.
- [ ] **Mem0 — optional extras**: `spaCy` (`pip install "mem0ai[nlp]"`) for more refined entity extraction; `fastembed` (`pip install "mem0ai[extras]"`) to enable BM25 keyword search alongside semantic search.
- [ ] **`chromadb`/`posthog` version conflict** (Section 7.4) — unresolved; currently sidestepped by not using CrewAI's default memory, not actually fixed.
- [ ] **Paperclip agent manager** — install and configure; will also be used in the future "Get Contractors Now" project.

## Notes

- This guide assumes a fresh Ubuntu install on the 500GB partition of the Samsung 990 PRO 2TB.
- Update model list in Section 2.2 as new models are added/removed.
- Update Section 3 if additional Docker containers (vector databases, n8n, etc.) are introduced later.
- Ollama is intentionally kept native, not dockerized — see the note at the top of Section 3.
- Section 3.5 (remote access) is a placeholder until that setup is actually done.
- Section 7 (CrewAI) runs in its own venv, separate from Mem0's (Section 5) — the two must never have the local Qdrant data open at the same time (see the note in 5.6).
