# AI_USAGE.md — Cultive8 BD Developer Assessment

**Candidate:** Md Radwan Ahamed  
**Project:** Local AI Security Log Analyzer ("LogSentinel")  
**Specification:** Offline execution, Local LLM via Ollama, 2,048-token limit per call, 4 GB RAM server budget.

---

## 1. Tools Used

- **Google Stitch (stitch.ai from Google):** Used to AI-generate the initial frontend UI for **"LogSentinel"** (HTML5, CSS, vanilla JavaScript) in a single portable file, based on detailed specification prompts for a quiet, dark, flat cybersecurity incident dashboard.
- **Claude / Antigravity Assistant:** Used as a pair-programming coding assistant for scaffolding boilerplate (Flask blueprint patterns, initial regex patterns, unit test templates).
- **Local Runtime AI:** `Qwen2.5 0.5B`, `Qwen3.5 0.8B`, and `Qwen3.5 2B` running via local Ollama (`http://localhost:11434`) strictly for offline log analysis. Zero cloud APIs used at runtime.
- **Manual Engineering & Debugging:** All architecture decisions, token chunking calculations, heuristic-AI hybrid pipeline design, prompt iterations, lifecycle state management (pause/resume/cancel/discard), and model failure mitigation were engineered and resolved by the developer.

---

## 2. Frontend AI Generation Prompts (Google Stitch / stitch.ai from Google)

The frontend interface for **LogSentinel** was explicitly AI-generated using **Google Stitch (`stitch.ai` from Google)**. The following sequential prompts were used to generate, polish, and harden the frontend interface:

### Prompt 1: Initial Frontend UI Generation (Google Stitch)
```text
Build a minimal, calm, readable web app, "LogSentinel", for analyzing server log files. The user uploads a log, watches it processed in parts, then reads one merged security report. Output one index.html (HTML5, CSS, vanilla JS, no frameworks, no external dependencies). Remove anything that does not help upload, monitor, or read results.

STYLE
- Dark, flat, quiet. No glows, gradients, blur, shadows, emojis, taglines. Hover and expand transitions only (150ms).
- System sans-serif for text; monospace only for IPs, line numbers, log evidence, JSON. Body 16px, secondary 14px, titles 20-24px, line height 1.6. Content column max 800px, centered, 48px between sections.
- Colors as CSS variables: bg #0e1116, surface #151a21 (drop zone and side panel only), hover #1b212a, divider #232a34, text #e6e9ee, text-secondary #8d98a8, muted #5f6a79, accent #4fd1b5 (buttons, links, progress, focus only), critical #f0616d, high #f4a259 (clearly orange), medium #e9c46a, low #6fcf97.
- Severity colors appear only as small dots, thin 3px edges, or chart marks, never as filled badges.
- Use whitespace and thin dividers instead of nested boxes. Every number appears once and must match everywhere.

NAV: "LogSentinel" left; Analyze, Report, Chunks right. One view at a time.

VIEW 1, ANALYZE
- Large drop zone (.log/.txt only). After selecting: one line with name, size, lines, estimated tokens.
- Model dropdown (Qwen3.5 0.8B, Qwen3.5 2B, Gemma 4 E2B), primary "Start analysis", text-button "Cancel" while running.
- Running state: big percentage, thin progress bar, one sentence ("Analyzing part 7 of 9, about 1 minute left"), a row of 9 dots (filled done, ringed running, hollow waiting), plain text "Memory 2.7 GB of 4 GB · Average call 18s", collapsible timestamped activity log.
- Errors are one line plus a Retry link (invalid type, empty, too large, model unreachable, cancelled). "Previous session found, 5 of 9 parts done" is one quiet line with Resume / Discard links.

VIEW 2, REPORT (compact, about two screens)
1. Summary: headline sentence, one plain detail sentence, then "Critical · 6 findings · 2,160 lines · 9 parts · 8m 42s · 1 part recovered" and "1 Critical · 2 High · 2 Medium · 1 Low" with dots. Top right: Readable/JSON switch, Download JSON, Download Markdown.
2. One chart, "Attack flow across the file": inline SVG, no panel behind it, hairline strokes only. A single baseline for the whole file split into 9 parts (P1-P9, with start line numbers in muted 10px monospace). Evidence lines are 6px dots on the baseline in severity color. Arcs connect the linked events of a finding in order, height growing with distance (1.5px, 55% opacity, final arc full opacity, final node ringed and labeled "Login succeeded"). Below the baseline, one 8px square per finding touching each part, stacked; parts with no findings show "clear". Arcs draw in once over 600ms. Hover highlights a finding and dims the rest with a tooltip (ID, title, line, excerpt); click scrolls to and expands that finding. One-line legend underneath.
3. Linked incident: vertical chain for findings spanning several parts, one row per step: line number, part, timestamp, description (failed logins in muted dots, final compromise in severity color and bold), then a bold one-sentence conclusion.
4. Findings: filter tabs (All, Critical, High, Medium, Low with counts) and IP search. Each finding is a two-line row: dot, ID, title, IP on the right; full reason underneath (wraps, never truncated) with "4 lines · Parts 1, 2, 4, 8". Accordion, one open at a time, first open by default. Expanded shows only Evidence (monospace, line-number gutter, suspicious part subtly highlighted with rgba(240,97,109,0.15), wrapping with hanging indent, max 5 lines then "show N more") and Suggested action (one sentence).
5. JSON view: same report pretty-printed with muted syntax colors (keys #8d98a8, strings #6fcf97, numbers #f4a259), line numbers, Copy button.
Empty result: "No confirmed attacks found."

VIEW 3, CHUNKS
Table: Part, Lines, Status, Time, Findings (queued parts show a dash, never a number; a timed-out part shows "Retrying (2 of 3)"). Clicking a row opens a right side panel with Readable and JSON tabs. Readable: 1-3 plain sentences, this part's findings as simple rows, "Carried to next part" bullets. JSON: model reply pretty-printed with Copy; if malformed and repaired, sub-tabs "Recovered" and "Raw output" plus a small "recovered" tag in the row. Esc closes the panel.

Chunk JSON shape: {"chunk":2,"line_range":[241,480],"findings":[{"attack_type":"brute_force","severity":"High","identifier":"203.0.113.44","evidence_lines":[253,261,270],"reason":"...","suggested_action":"..."}],"carry_forward":["203.0.113.44: 3 failed logins in L253-L270"]}

DATA RULES
File has 2,160 lines in 9 parts of 240. Derive part = ceil(line/240) and x = line/2160 in code; never hand-write them.
Demo findings (all 9 parts complete for the report; part 3 was recovered):
- F-01 Critical: brute force then account takeover, 203.0.113.45, lines 12, 418, 903, 1740 (parts 1, 2, 4, 8)
- F-02 High: SQL injection, 203.0.113.72, lines 265, 271, 733, 740, 748 (parts 2, 4)
- F-03 High: path traversal to /etc/passwd, 203.0.113.90, lines 790, 794, 801 (part 4)
- F-04 Medium: scanning for /.env and .git, 203.0.113.90, lines 810, 812, 815, 819 (part 4)
- F-05 Medium: API rate abuse, 203.0.113.155, lines 1010, 1012, 1015, 1019, 1022, 1025 (part 5)
- F-06 Low: malformed request header, 198.51.100.88, lines 1304, 1311 (part 6)
Use realistic access-log lines with timestamps increasing with line number.

CODE
CSS and JS inline. Separate API section of placeholder functions returning mock data: listModels, uploadLog, startAnalysis, getProgress, getChunkResults, getReport, cancelAnalysis, resumeSession. One render function per view. Insert log text with textContent only. Semantic HTML, ARIA labels, keyboard accessible, visible focus, responsive to tablet width, no layout shift.
```

### Prompt 2: Refinement & Polish Pass (Google Stitch)
```text
Polish pass only. Do not add features. Remove every border, background and label that is not needed. Increase vertical spacing by 1.5x. Make sure no text is clipped or truncated anywhere (evidence lines wrap with a hanging indent). Keep one accent color. Check that every count, part number and line number agrees across the summary, chart, chain, filter tabs, findings and chunks table. Align the chart's colors, fonts and spacing with the rest of the page so it feels part of the same system.
```

### Prompt 3: API Integration & Robustness (Google Stitch)
```text
Keep the design unchanged. Improve the code: move all data access into one api object with the functions listModels, uploadLog, startAnalysis, getProgress (polled every 2s), getChunkResults, getReport, cancelAnalysis, resumeSession, each with a clear comment on the expected request and response JSON. Keep mock data behind a single USE_MOCK flag. Render everything from the response data, with no hardcoded numbers in the HTML. Add loading, error and empty states to every view. Make the JSON viewer and Copy button work with real data, and make Download JSON and Download Markdown generate the files from the current report. Handle malformed API responses without crashing the page.
```

### Developer's Engineering & Integration Pass (Manual Polish & Architecture):
While Google Stitch created the initial UI mockup and styling rules, the following production engineering was manually implemented:
1. **Live REST API Wiring:** Replaced client-side mock placeholders with dynamic `fetch()` calls to Flask endpoints (`/api/analyze`, `/api/status/<id>`, `/api/pause/<id>`, `/api/resume/<id>`, `/api/cancel/<id>`, `/api/discard/<id>`, and `/api/active-session`).
2. **Upload Lockdown & State Synchronization:** Hardened upload inputs and drag-and-drop zones against concurrent analysis requests, resolving race conditions between backend workers and frontend polling loops.
3. **Report Simplification & Investigation Sidebar Redesign:** Replaced multi-card scroll sprawl with a clean, focused 3-section layout (Executive Summary, Overall Attack Flow Graph, Findings list) and an interactive right-side drawer displaying attack-specific SVG timelines, correlated threats, evidence gutters, structured remediation actions, and detection reasoning.

---

## 3. Key Coding Prompts (Assistant Interaction)

Below are representative prompts used during backend development with the coding assistant, along with what was accepted vs. what had to be modified:

### Coding Prompt 1: Chunking & Memory Architecture
> *"How should I architect a Flask background processing worker that processes a large file in small batches, stores job state in-memory without exceeding 4GB RAM, and provides polling endpoints for progress?"*
- **What AI Suggested:** A generic `threading.Thread` with an in-memory dictionary.
- **Developer Changes:** Adapted it to enforce sequential one-call-at-a-time execution (no concurrent LLM threads that would blow up memory) and added atomic progress percentage steps.

### Coding Prompt 2: Robust LLM JSON Extraction
> *"How do I parse structured JSON arrays from small local LLMs when the model sometimes wraps responses in markdown codeblocks or injects extraneous conversational tokens?"*
- **What AI Suggested:** Standard `json.loads` inside a regex search `r'\{[\s\S]+\}'`.
- **Developer Changes:** Small models often output multi-line lists or mixed objects. I built a multi-stage parser: markdown fence stripper → whole-array JSON parser → curly-brace block iterator → line-by-line fallback.

---

## 4. Local Model Prompts (Runtime AI Engine)

### Chunk Analysis Prompt
```text
You are a cybersecurity log analyst. Examine these server logs (part {chunk_idx+1}/{total_chunks}).
{PREVIOUS_FINDINGS_CONTEXT}

LOGS:
{decoded_lines_text}

Look for confirmed attacks:
- SQL injection: SQL commands like UNION, SELECT, OR 1=1 in query parameters
- Brute force: multiple failed logins (auth=invalid_password)
- Account compromise: success login (auth=success) following earlier failed logins from same IP
- Reconnaissance/Scanning: requests for .env, .git, phpmyadmin, wp-admin, backup.sql
- Path traversal: ../ or /etc/passwd in path
- Rate abuse: high request counts (e.g. 100+ requests in 10s)
- Data exfiltration: large data exports

Output a JSON array of findings. If no attacks, output [].
Each finding object MUST have:
{"type":"<attack_type>","severity":"Low|Medium|High|Critical","ip":"<ip>","lines":[<line_numbers>],"evidence":"<quoted path or message>","reason":"<why malicious>","action":"<recommended action>"}

Respond ONLY with the JSON array: ###
```

### Final Incident Summary Prompt
```text
You are a senior security lead. Combine these raw security events into ONE cohesive executive incident report.

EVENTS DETECTED:
{merged_findings_json}

Merge related events into attack chains (e.g., link brute force attempts to subsequent successful logins and data exports).
Output a JSON object with this exact structure:
{
  "summary": "2-3 sentence executive summary of overall incidents",
  "total_threats": <number_of_distinct_attacks>,
  "attack_chains": [
    {
      "chain_id": "chain-1",
      "attack_type": "...",
      "severity": "Critical|High|Medium|Low",
      "actors": ["ip1"],
      "timeline": "chronological sequence of events",
      "lines": [line_numbers],
      "evidence": "quoted evidence",
      "reason": "why this is an attack",
      "action": "immediate mitigation"
    }
  ],
  "top_malicious_ips": ["ip1", "ip2"],
  "recommendations": ["rec1", "rec2", "rec3"]
}
Respond ONLY with the JSON object: ###
```

---

## 5. Prompt Changes & Iterations

| Iteration | Change Made | Technical Rationale |
|---|---|---|
| **v1 (Initial)** | Free-form analytical prompt requesting prose analysis. | Small model outputs varied wildly and could not be parsed reliably by the backend. |
| **v2 (JSON Objects)** | Required single JSON object per line. | The model struggled with strict multi-line delimiters and sometimes emitted invalid JSON commas. |
| **v3 (Stop Tokens)** | Added `###` stop token and set `temperature=0.1`. | Stopped model from appending hallucinatory conversational text after closing JSON braces. |
| **v4 (Line Decoding)** | Pre-decoded URL strings (e.g. `%27` to `'`, `%20` to space) and stripped noise fields before prompt insertion. | Reduced token consumption per chunk from ~1,100 to ~400 tokens; enabled 0.5B model to clearly see SQL injection tokens. |
| **v5 (Strict Negation Filter)** | Instructed model to return `[]` when clean and added Python-side rejection of negative assertions. | Eliminated false-positive "No attack detected" cards generated by small model checklists. |

---

## 6. Token Budget Plan (Under 2,048 Limit)

The assessment specifies a hard limit of **2,048 tokens per model call**.

| Component | Token Allocation | Strategy |
|---|---|---|
| **System Persona & Rules** | ~140 tokens | Concise, directive instructions. |
| **Carried Context (Links across chunks)** | ~90 tokens | Compressed summary of last 6 active findings (`type`, `ip`, `lines`). |
| **Log Chunk (30 lines optimized)** | ~400–450 tokens | Stripped unneeded telemetry (`request_id`, `host`, `duration_ms`), keeping only security-relevant fields (`IP`, `method`, `path`, `status`, `auth_result`). |
| **Reserved Output Budget** | ~512 tokens | Configured via Ollama `num_predict: 512`. |
| **Safety Headroom Buffer** | ~850 tokens | Unused space preventing context overflow. |
| **Total Prompt + Response** | **~1,150–1,200 tokens** | **Well within the 2,048 token ceiling.** |

---

## 7. Critical Model Limitation Discovered & Solved by Developer

> **The Problem Which the AI Coding Assistant Failed to Predict:**
> 
> During end-to-end integration testing with `qwen2.5:0.5b`, the AI coding assistant assumed standard prompting would work. However, when a sub-billion parameter model is given an attack taxonomy checklist, it exhibits a well-known small-model limitation: **it treats the checklist as a template to fill out**.
> 
> The model generated 7 separate cards with:
> - `Evidence: "No SQL injection detected."`
> - `Why: "No SQL injection detected."`
> - `Action: "No action required."`
> - Placeholder action strings copied verbatim: `"action": "recommended mitigation"`.
> - Empty line number arrays `lines: []`.

### Developer's Independent Analysis & Resolution:
1. **Identified the Failure Mechanism:** Realized the model lacked the capacity to both perform zero-shot deduction across 30 raw JSON lines and generate nuanced security actions simultaneously.
2. **Hybrid Security Engine Architecture:**
   - Designed a deterministic log feature extractor in `core/parser.py` that isolates suspicious event signatures (URL-encoded SQL payloads, traversal sequences, failed auth counters, bulk exports).
   - Paired this with local model validation and reasoning.
   - Built a **Threat Enrichment & Remediation Engine** in `core/analyzer.py` mapping normalized attack categories to deep technical reasons and specific mitigation actions (e.g. WAF rules, parameterized queries, session invalidation, MFA enforcement).
3. **Strict Evidence & Line-Number Guardrail:** Added a strict validator ensuring that any finding lacking concrete line numbers or asserting a negative evidence string is rejected before reaching the final report.

---

## 8. Examples of AI Mistakes I Fixed

1. **Hallucinated Attack Attribution to Line 1:**
   - *AI Mistake:* When grouping failed login attempts, the assistant's code naively picked `chunk[0].get("client_ip")`, incorrectly blaming normal user IP `198.51.100.90` for the brute force attack occurring on line 5.
   - *Fix:* Re-engineered `failed_by_ip` as a `defaultdict(list)` to track authentication failures per individual client IP, correctly pinning all 12 failed attempts on `203.0.113.44`.

2. **Cross-Chunk Disconnection (Brute Force to Compromise):**
   - *AI Mistake:* The model initially treated failed logins on lines 5–189 as isolated events from the successful login on line 196 and the CSV export on line 201.
   - *Fix:* Built the `saved_context` forward-injection mechanism to pass earlier attacker IPs into subsequent chunk prompts, allowing the system to assemble the complete kill-chain: **Brute Force → Account Compromise → Data Exfiltration**.

3. **Malformed Markdown JSON Wrap in Final Summary:**
   - *AI Mistake:* Ollama frequently wrapped JSON objects in ` ```json ... ``` ` fences, causing `json.loads` in Flask to raise exceptions and default to an empty report.
   - *Fix:* Implemented regex pre-cleaning `re.sub(r'```(?:json)?|```', '', raw)` and structural regex object extraction `re.search(r'\{[\s\S]+\}', raw)` to guarantee clean parsing.

4. **Model Name 404 Discrepancy:**
   - *AI Mistake:* Code hardcoded `qwen3.5:0.8b` based on the brief's suggested model, but when running on a fresh Ollama instance with `qwen2.5:0.5b`, Ollama threw `404 Not Found`.
   - *Fix:* Added runtime auto-discovery in `core/model.py` that queries `/api/tags` and dynamically binds to whichever compatible model is currently installed.
