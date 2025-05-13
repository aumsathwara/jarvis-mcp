### DEPLOYMENT.md

*A guide to launching **Jarvis-MCP** anywhere — local or remote, stdio or SSE.*

---

## 0.  TL;DR check-list

| 🔧 Step                                                          | Why                                              |
| ---------------------------------------------------------------- | ------------------------------------------------ |
| `python -m venv .venv && source .venv/bin/activate`              | Isolate deps                                     |
| `pip install -r requirements.txt && pip install -e .`            | Install server & client                          |
| Create a **`.env`**                                              | Set `MCP_TRANSPORT=sse` (else stdio) + host/port |
| `mcp-server`                                                     | Run server (`stdio` or `SSE` decided by env)     |
| `mcp-client`                                                     | Talk to it (same env vars)                       |
| **Docker?** → build image → `docker run -p 3001:3001 jarvis-mcp` | Remote or reproducible deploy                    |
| **Port 3001 open?**                                              | The #1 cause of “Server disconnected” errors     |

---

## 1. Environment variables & `.env`

`server.py` looks only at three variables:

| Variable        | Default   | Meaning                                  |
| --------------- | --------- | ---------------------------------------- |
| `MCP_TRANSPORT` | `stdio`   | `stdio` \| `sse`                         |
| `MCP_SSE_HOST`  | `0.0.0.0` | Interface to bind (`0.0.0.0` in Docker!) |
| `MCP_SSE_PORT`  | `3001`    | Port for SSE                             |
| `GEMINI_API_KEY`| `{your_api}`| LLM Client for MCP tool calls         |

The first `load_dotenv()` call means if a file named **`.env`** exists in the *current working directory* it will override the shell.

### Example  `.env`

```dotenv
# Run an SSE server on port 8000, listening only on loopback:
MCP_TRANSPORT=sse
MCP_SSE_HOST=127.0.0.1
MCP_SSE_PORT=8000
GEMINI_API_KEY={your_api_key}
```

### Setting at runtime

```bash
# Linux/macOS
export MCP_TRANSPORT=sse
export MCP_SSE_HOST=0.0.0.0
export MCP_SSE_PORT=3001
export GEMINI_API_KEY={your_api_key}
mcp-server
```

```powershell
# Windows PowerShell
$Env:MCP_TRANSPORT = "sse"
$Env:MCP_SSE_HOST  = "127.0.0.1"
$Env:MCP_SSE_PORT  = "8000"
$Env:GEMINI_API_KEY={your_api_key}
mcp-server
```

---

## 2. Deployment Scenarios

### 2.1  Local  — stdio   *(zero-config)*

| Server        | Client       | Command                                        |
| ------------- | ------------ | ---------------------------------------------- |
| same terminal | `mcp-client` | No vars needed; client spawns server via stdio |

- Nothing to configure, Inspector works with `mcp dev`.

---

### 2.2  Local — SSE

```bash
# Terminal 1 (server)
echo "MCP_TRANSPORT=sse" > .env
mcp-server                  # binds http://127.0.0.1:3001/sse
#or
python src/jarvis_mcp/server.py

# Terminal 2 (client)
mcp-client                  # auto-reads .env and connects over SSE
#or
python src/jarvis_mcp/client.py
```
> [!NOTE]
 > One can create .env inside src/jarvis_mcp with environment variables

**Smoke-test**

```bash
curl -N -H "Accept: text/event-stream" http://localhost:3001/sse
# Connection stays open → OK.
```

---

### 2.3  Local → Remote 🌐  (SSE)

You develop on your laptop but run Jarvis-MCP on a lab workstation or VM.

```
 [local mcp-client]  <--SSE-->  [remote mcp-server]
```

1. **SSH onto remote host**

   ```bash
   ssh user@remote
   git clone https://github.com/aumsathwara/jarvis-mcp.git
   cd jarvis-mcp
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt && pip install -e .
   export MCP_TRANSPORT=sse MCP_SSE_HOST=0.0.0.0 MCP_SSE_PORT=8000
   mcp-server
   ```
2. **Open firewall** (`sudo ufw allow 8000/tcp` or security-group rule).
3. **Local client**

   ```bash
   export MCP_TRANSPORT=sse
   export MCP_SSE_HOST=remote-ip-or-dns
   export MCP_SSE_PORT=8000
   mcp-client
   ```

*Optional*: use SSH port-forward instead of opening a port:

```bash
ssh -L 8000:localhost:8000 user@remote
mcp-client  # connects to localhost:8000 which tunnels to remote
```

---

### 2.4  Remote → Remote 🌐  (SSE, containerised)

Target cloud VM / K8s node; users connect from *other* machines.

```
[user] --HTTP/SSE--> [Reverse-Proxy] --HTTP--> [Docker jarvis-mcp]
```

1. **Build & push image**

   ```bash
   docker build -t jarvis-mcp:latest .
   docker push jarvis-mcp:latest
   ```

2. **Run on the server**

   ```bash
   docker run -d --name jarvis-mcp \
     -e MCP_TRANSPORT=sse \
     -e MCP_SSE_HOST=0.0.0.0 \
     -e MCP_SSE_PORT=3001 \
     -p 3001:3001 \
     jarvis-mcp:latest
   ```

3. **TLS / reverse-proxy (nginx, Traefik, Caddy)**
   Terminate HTTPS and proxy `/sse` & `/messages` to `localhost:3001`.

4. **Clients**

   ```bash
   export MCP_TRANSPORT=sse
   export MCP_SSE_HOST=your.domain.com
   export MCP_SSE_PORT=443   # or 80 if plain
   mcp-client
   ```

---

## 3. Docker-file cheat-sheet

```dockerfile
# Dockerfile
FROM python:3.12-slim

# install git for pip‐editable VCS installs
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# bring in project metadata
COPY pyproject.toml requirements.txt ./

# copy your code
COPY src/ ./src/

# install uvicorn + your MCP package + its git‐hosted deps
RUN pip install --upgrade pip \
 && pip install uvicorn \
 && pip install \
      -r requirements.txt \
      -e . 

# default to SSE on 127.0.0.1:3001
ENV MCP_TRANSPORT=sse \
    MCP_SSE_HOST=0.0.0.0 \
    MCP_SSE_PORT=3001
    
EXPOSE 3001

CMD ["python", "src/jarvis_mcp/server.py"]

```

---

## 4. Troubleshooting

| Symptom                                                          | Likely Cause                                                   | Fix                                                           |
| ---------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------- |
| `httpx.RemoteProtocolError: Server disconnected…` (client side)  | Server bound to **127.0.0.1** **inside** Docker or remote host | Set `MCP_SSE_HOST=0.0.0.0` and rebuild/restart                |
| `curl: (52) Empty reply`                                         | Firewall / port not open                                       | `docker run -p 3001:3001`, open security-group, or SSH tunnel |
| `ValueError: Functions with **kwargs are not supported as tools` | A tool signature still contains `**kwargs`                     | Refactor tool: accept explicit `extra_args: dict = None`      |
| Server prints `No configuration was found. Run jarvis init…`     | JarvisManager hasn’t been initialized; harmless warning        | Call `jm_create_config` once or ignore                        |
| `mcp-client` “Connected via SSE” then immediately exits          | Server died → check `docker logs` or terminal 1 for trace      |                                                               |
| Tool returns *“Append failed: Could not find pkg: hermes”*       | Package doesn’t exist in repo                                  | Run `jm_list_repos`, `jm_add_repo`, or fix typos              |

---

## 5. Customising the `.env`

Add anything you want—`GEMINI_API_KEY`, extra Jarvis paths, etc. Example:

```dotenv
# MCP transport
MCP_TRANSPORT=sse
MCP_SSE_HOST=0.0.0.0
MCP_SSE_PORT=3001

# Gemini LLM
GEMINI_API_KEY=YOUR_API_KEY_HERE

# Jarvis paths (override JarvisManager defaults)
JARVIS_CONFIG_DIR=/data/jarvis/config
JARVIS_PRIVATE_DIR=/data/jarvis/private
```

Place the file **next to the command you run** (server *and* client each read their own cwd).

---

### You’re ready!

Pick a deployment mode, set the three env vars, and fire up **`mcp-server`**.
Run **`mcp-client`** from anywhere to create pipelines, append packages, or monitor resource graphs.
