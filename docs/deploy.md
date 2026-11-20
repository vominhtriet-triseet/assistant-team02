# Deploy on the GPU PC behind Cloudflare Tunnel

Everything runs on one Windows PC (32 GB RAM, RTX 5070 12 GB): the assistant, Ollama,
and `cloudflared`. Visitors reach it at https://assistant.triseet.site. Only the
assistant's port 8000 is published; Ollama's port 11434 stays on the PC.

```text
browser ── HTTPS ──> Cloudflare ── tunnel ──> cloudflared (PC) ──> 127.0.0.1:8000 assistant ──> 127.0.0.1:11434 Ollama
```

## Already configured in Cloudflare (Nov 2026)

| Item | Value |
|---|---|
| Zone | `triseet.site`, Free plan, nameservers on Cloudflare |
| Tunnel | `assistant-team02` (Networking → Tunnels), connector installed as a Windows service |
| Route | `assistant.triseet.site` → `http://127.0.0.1:8000` (CNAME created automatically) |
| Rate limit | Security rules → "Limit assistant chat API": more than 8 requests in 10 s to `/api/chat` from one IP is blocked for 10 s |
| HTTPS | SSL mode Full, Always Use HTTPS on |
| Access | Public (no Cloudflare Access login) |

## 1. Local model with Ollama

1. Install Ollama from https://ollama.com/download. It starts with Windows and listens on `http://localhost:11434`.
2. Download the model (about 9 GB, fits in 12 GB VRAM with room for context):

   ```bash
   ollama pull qwen3:14b
   ```

3. Check it answers in Vietnamese:

   ```bash
   ollama run qwen3:14b "Trả lời ngắn: thủ đô của Việt Nam là gì?"
   ```

Why `qwen3:14b`: it is trained on many languages including Vietnamese, returns clean
JSON, and grades free-text answers well. The assistant turns its "thinking" mode off so
replies come back quickly. If replies are slow, use `qwen3:8b` (about 5 GB) instead.

## 2. The assistant

In PowerShell, in the folder where you keep projects:

```bash
git clone https://github.com/vominhtriet-triseet/assistant-team02.git
```

```bash
cd assistant-team02
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Create `.env` next to `README.md`:

```text
ASSISTANT_LLM=ollama
ASSISTANT_LLM_MODEL=qwen3:14b
```

Start it and check:

```bash
python -m assistant serve
```

The first line must say `AI provider: ollama`. Open http://127.0.0.1:8000 on the PC,
then https://assistant.triseet.site from a phone. A 502 error from the domain means the
tunnel works but the assistant is not running.

## 3. Start the assistant with Windows

Ollama and `cloudflared` already start on their own. Register the assistant as a task
that runs at logon (replace the path with your clone):

```bash
schtasks /Create /TN "assistant-team02" /SC ONLOGON /RL LIMITED /TR "\"C:\path\to\assistant-team02\.venv\Scripts\pythonw.exe\" -m assistant serve"
```

`pythonw.exe` runs without a console window. The working directory does not matter: the
assistant finds `.env`, `data/`, and `ui/` from its install location. Stop it with
`schtasks /End /TN "assistant-team02"`, remove it with `schtasks /Delete /TN "assistant-team02"`.

## 4. Update to a new version

```bash
schtasks /End /TN "assistant-team02"
git pull
python -m pip install -e .
schtasks /Run /TN "assistant-team02"
```

`data/assistant.db` is not in Git, so students' plans and notes are kept across updates.
Back it up by copying the file while the assistant is stopped.

## Checks when something is wrong

| Symptom | Check |
|---|---|
| Domain shows 530 / 1033 | `Get-Service cloudflared` must be Running; the tunnel must be Healthy in the dashboard |
| Domain shows 502 | The assistant is not running on port 8000 |
| Reply warns "AI service is unavailable" | `ollama list` shows `qwen3:14b`; http://localhost:11434 answers "Ollama is running" |
| First AI reply is slow | The model loads into VRAM once (10 to 20 s); it then stays loaded for 30 minutes |
| A visitor gets HTTP 429 or a block page | The rate limit rule; raise it in Security rules if real users hit it |

## Privacy

The site is public. Anyone with the link gets their own empty session, identified by a
random id stored in their browser; nobody can see another visitor's plan or notes. The
data stays on the PC in `data/assistant.db`. Tell students not to save passwords or
personal data in notes.
