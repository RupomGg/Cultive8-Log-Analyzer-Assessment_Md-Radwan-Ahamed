# Local AI Security Log Analyzer ("LogSentinel")

> A minimal, calm, and robust offline web application that uses a **local language model** (via Ollama) to detect, correlate, and investigate security attacks in server logs. Operates strictly offline within a **4 GB RAM ceiling** and a **2,048-token limit per call**.

---

## 🚀 Quick Start

### Option A: One-Click Launcher (Windows)
Double-click `start.bat` in the root folder. It will automatically:
1. Verify Ollama installation (or prompt to download).
2. Start the local Ollama service.
3. Pull the recommended `qwen3.5:0.8b` model if missing.
4. Install backend dependencies into your local Python environment.
5. Launch the Flask backend on `http://localhost:5000`.
6. Open `frontend/index.html` directly in your default browser.

### Option B: Manual Setup

#### 1. Start Ollama and Pull a Model
```bash
# Download and install Ollama from https://ollama.com
ollama serve

# Pull the brief-recommended model (~600 MB)
ollama pull qwen3.5:0.8b
```

#### 2. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 3. Start the Backend Server
```bash
python app.py
# Server starts on http://localhost:5000
```

#### 4. Open the Frontend
Open `frontend/index.html` directly in any web browser — no Node.js, npm, or build step required.

---

## 🧠 Supported Local Models

| Model | Size | RAM Used | Inference Speed | Notes |
|---|---|---|---|---|
| `qwen3.5:0.8b` ⭐ | ~600 MB | < 1.0 GB | ⚡ Fast (1–2s / chunk) | **Default & brief-recommended** |
| `qwen3.5:2b` ⭐ | ~1.5 GB | ~1.8 GB | Moderate (3–5s / chunk) | **Brief-recommended** (deeper deductive nuance) |
| `gemma4:e2b` ⭐ | ~1.0 GB | ~1.3 GB | Fast (2–3s / chunk) | **Brief-recommended** |
| `qwen2.5:0.5b` | ~400 MB | < 0.8 GB | ⚡⚡ Fastest | Ultra-lightweight fallback |

The application automatically queries `/api/tags` on Ollama to populate available models and allows dynamic switching from the UI during runtime.

---

## 📊 Chunking & Context Linking (2,048-Token Limit)

To process arbitrarily large log files without exceeding the **2,048-token context ceiling** or exhausting memory:
1. **Sanitization:** Strips non-essential log fields (`duration_ms`, `host`, internal IDs) and pre-decodes URL query parameters.
2. **Deterministic Partitioning:** Splits entries into chunks of **30 lines** each (~400–450 tokens), leaving ~1,600 tokens for system rules, context, and output response.
3. **Model Call Optimization:** Skips model execution on static benign traffic (e.g., pure CSS/JS assets returning 200/304), saving model calls and inference latency.
4. **Context Forwarding:** The last 6 active security findings (attacker IP, attack type, evidence lines) are compressed into a forward-injected prompt context. This enables the model to connect events occurring across chunk boundaries (e.g., failed logins in Chunk 1 linked to account compromise in Chunk 2).

```
Full Log File (e.g., 258 lines)
  ├── Chunk 1 (L1–L30)    → Model Inference → Findings 1
  ├── Chunk 2 (L31–L60)   → Carried Context + Chunk 2 → Findings 2
  ├── Chunk 3 (L61–L90)   → Static Benign Traffic → Optimized (Model call skipped)
  ├── ...
  └── Summary Phase       → Incident Aggregation → Merged Multi-Stage Kill Chains
```

---

## 🎯 Verified Threats in Sample Log (`Cultive8_Workspace_Agrigen_Server.log`)

| Finding ID | Attack Classification | Severity | Hostile IP | Affected Lines | Attack Chain Description |
|---|---|---|---|---|---|
| **F-01** | Account Compromise | **Critical** | `203.0.113.44` | L18 | Successful administrative login (`auth=success`) following credential guessing. |
| **F-02** | Brute Force Authentication | **High** | `203.0.113.44` | L10, L12, L14, L16 | 4 consecutive failed password attempts targeting `workspace.admin`. |
| **F-03** | SQL Injection Probing | **Critical** | `203.0.113.72` | L29, L30, L222, L223 | Boolean tautologies (`' OR 1=1--`) and `UNION SELECT` schema enumeration. |
| **F-04** | Unauthorized Data Exfiltration | **Critical** | `203.0.113.44` | L245 | High-volume 2.8 MB CSV export executed via compromised administrative session. |
| **F-05** | Reconnaissance / Scanning | **Medium** | `203.0.113.90` | L5, L8, L12, L50, L52 | Automated scanner probing for sensitive dotfiles (`.env`, `.git`) and admin portals. |
| **F-06** | Path Traversal / LFI | **High** | `203.0.113.90` | L60, L61, L62 | Directory escape sequences (`../../etc/passwd` & double URL-encoded `%252e`). |

---

## 📁 Project Directory Structure

```
log-analyzer/
├── .github/
│   └── workflows/
│       └── backend-tests.yml        # Automated GitHub Actions CI test suite
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                # REST API endpoints (analyze, status, pause, resume, cancel, discard, active-session)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── analyzer.py              # Chunk processing loop, threat enrichment, telemetry & checkpoint recovery
│   │   ├── model.py                 # Resilient Ollama client with retry backoff & dynamic model detection
│   │   ├── parser.py                # Fast log parser, token stripper & chunking engine
│   │   └── prompts.py               # Strict-schema chunk & summary security prompt templates
│   ├── tests/                       # Pytest test suite (24 unit & integration tests)
│   │   ├── test_analyzer_merge.py   # Finding deduplication, line normalization & fallback tests
│   │   ├── test_api.py              # Upload lockdown, 409 conflict, pause/cancel/discard endpoint tests
│   │   ├── test_config.py           # Configuration override & default tests
│   │   ├── test_model.py            # Ollama health check & retry backoff tests
│   │   ├── test_parser.py           # Log parsing & token-safe chunking tests
│   │   ├── test_pipeline.py         # End-to-end multi-chunk pipeline integration tests
│   │   └── test_prompts.py          # Prompt structure & schema constraint tests
│   ├── uploads/                     # Sandboxed uploaded logs & atomic JSON checkpoints
│   │   └── .gitkeep
│   ├── app.py                       # Flask application entrypoint with CORS & blueprint registration
│   ├── config.py                    # Centralized settings & environment variable parsing
│   └── requirements.txt             # Minimal Python dependencies (Flask, requests, psutil, pytest)
├── frontend/
│   ├── index.html                   # Single-page UI (AI-generated via Google Stitch, vanilla JS/CSS)
│   ├── code.html                    # Synchronized portable standalone markup
│   └── screen.png                   # Dashboard UI visual reference
├── start.bat                        # Automated 1-click launch script for Windows
├── README.md                        # Project architecture, instructions, and threat analysis
└── AI_USAGE.md                      # Comprehensive AI engineering log with Google Stitch prompts
```

---

## 🎨 UI Architecture: Simplified 3-Section Report + Details Drawer

The frontend was initially AI-generated using **Google Stitch (`stitch.ai` from Google)** and customized for focused investigation:

1. **Executive Summary (Top):** Compact headline summary, core metrics, and severity distribution badges.
2. **Overall Attack Flow Graph (Middle):** Hairline SVG timeline with interactive event nodes, severity coloring, and chunk density matrix. Clicking any node opens the right-side investigation sidebar.
3. **Findings Section (Bottom):** Severity filter tabs (All, Critical, High, Medium, Low), live IP search, and finding rows with line occurrences and inspect triggers.
4. **Interactive Attack Details Sidebar (Slide-in Right Drawer):**
   - **Attack Overview:** Taxonomy, hostile IP, severity, partition and line references, and narrative.
   - **Attack-Specific Progression Graph:** Dedicated SVG timeline of the selected attack with animated bezier arcs and pulsing terminal nodes.
   - **Correlated Attacks & Kill Chains:** Clickable threat cards explaining shared IP, chronological relationships, and kill chain progression (navigates within sidebar).
   - **Supporting Evidence:** Formatted log lines with line-number gutters and highlighted attack payloads.
   - **Suggested Remediation:** Prioritized actionable defense measures (action, why necessary, threat addressed, security benefit).
   - **Detection Reasoning:** Matched signatures, explicit `[Observed Evidence]` vs `[Inferred Analysis]` badges, and severity justification.

---

## ⚙️ System Requirements & Constraints

| Metric | Budget / Limit | Implementation Reality |
|---|---|---|
| **RAM Budget** | 4.0 GB total | Max ~1.6 GB used (Model ~600 MB + Flask ~45 MB + OS) |
| **Token Limit** | 2,048 tokens / call | Max ~1,150–1,200 tokens per chunk prompt |
| **Hardware** | Pure CPU inference | Automatic fallback via Ollama; no GPU required |
| **Network** | 100% Offline | Zero external cloud APIs; local requests to `127.0.0.1:11434` only |

---

## 🛡️ Security & State Reliability

- **Single Active Analysis Enforcement:** File uploads are locked both on the frontend (pointer events, disabled input, drag/drop guards) and backend (HTTP `409 Conflict` if a job is running).
- **Graceful Thread Suspension:** Pause and Cancel controls use cooperative worker flags evaluated before and after model calls for sub-second responsiveness without corrupted memory.
- **Crash Recovery & Checkpointing:** State is saved to `*_checkpoint.json` after every chunk. Restarting the backend preserves job progress without data loss.
- **Single Source of Truth:** `GET /api/active-session` prevents ghost/stale job resurrection across browser refreshes.
- **Command Injection Prevention:** Server log lines are treated strictly as data literals; prompts instruct the LLM never to execute log contents.

---

## ⚠️ Known Limits

1. **Context Window Constraint (2,048 Tokens):** Exceptionally long individual log entries (e.g., massive URI query strings or stack traces exceeding ~1,200 tokens) are safely truncated by the parser to guarantee that the chunk prompt remains under the strict 2,048-token context ceiling.
2. **Sub-Billion Parameter Model Nuance:** While `qwen3.5:0.8b` and `qwen2.5:0.5b` run exceptionally fast on CPU and comfortably fit within RAM, subtle multi-stage attack deductions benefit from larger models (e.g., `qwen3.5:2b` or `gemma4:e2b`). The app provides runtime model switching in the UI to toggle between them easily.
3. **Single Active Analysis Constraint:** To guarantee that memory consumption never exceeds the 4 GB RAM server ceiling, concurrent background analysis jobs are intentionally restricted. New uploads are blocked until the current job finishes, fails, is paused, or is cancelled.
4. **Local Ollama Daemon Dependency:** The application requires the local Ollama daemon to be running at `http://localhost:11434`. If Ollama is offline or unreachable, the system activates deterministic signature extraction as a fallback and warns the user via the connection status bar.

---

## ✨ Features Implemented

- [x] **Strict Offline Local AI:** Powered by Ollama (`qwen3.5:0.8b` default).
- [x] **Deterministic Chunking & Token Safety:** Strict 30-line chunks staying under 2,048 tokens.
- [x] **Context Carry-Forward:** Links multi-stage attacks across partition boundaries.
- [x] **Model Call Reduction:** Skips static benign log chunks to preserve CPU and RAM.
- [x] **Runtime Model Switching:** Dynamically detects installed Ollama models from the UI.
- [x] **Crash-Resilient Checkpoints:** Resumes partially analyzed logs after server restart.
- [x] **Real-Time Telemetry:** Live RAM consumption and average model latency metrics.
- [x] **3-Section Simplified Report:** Compact overview with deep interactive sidebar drawer.
- [x] **Cooperative Pause / Resume / Cancel:** Full backend thread control and state cleanup.
- [x] **Report Export:** Instant export to formatted JSON and executive Markdown reports.
- [x] **Automated Test Suite:** 24 unit and API tests in pytest covering all modules.
