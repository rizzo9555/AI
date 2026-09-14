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

### 3.1 Install Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Verify Docker:

```bash
sudo docker run hello-world
```

### 3.2 NVIDIA Container Toolkit (GPU access inside Docker)

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 3.3 Run Open WebUI

```bash
docker run -d \
  --name open-webui \
  --gpus all \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

Access the interface at:

```
http://localhost:3000
```

> Note: Open WebUI will connect to the local Ollama instance automatically via `host.docker.internal`. If it doesn't detect Ollama, set the `OLLAMA_BASE_URL` environment variable manually (e.g. `-e OLLAMA_BASE_URL=http://host.docker.internal:11434`).

### 3.4 Verify

```bash
docker ps
docker logs open-webui
```

---

## 4. Post-Install Checklist

- [ ] `nvidia-smi` shows the RTX 4080 SUPER correctly
- [ ] `ollama list` shows all 8 models
- [ ] Open WebUI loads at `http://localhost:3000`
- [ ] Open WebUI can see and query the Ollama models
- [ ] GPU usage confirmed during inference (`nvidia-smi` while running a prompt)

---

## Notes

- This guide assumes a fresh Ubuntu install on the 500GB partition of the Samsung 990 PRO 2TB.
- Update model list in Section 2.2 as new models are added/removed.
- Update Section 3 if additional Docker containers (vector databases, n8n, etc.) are introduced later.
