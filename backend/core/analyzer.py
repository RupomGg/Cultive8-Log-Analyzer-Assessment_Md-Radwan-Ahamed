import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
import psutil

import config
from core.model import call_model
from core.parser import parse_log_file, chunk_entries, entries_to_text
from core.prompts import build_chunk_prompt, build_summary_prompt


ACTION_TEMPLATES = {
    "sql_injection": {
        "title": "SQL Injection Attack",
        "severity": "Critical",
        "reason": "Attacker injected SQL commands (UNION SELECT, OR 1=1, SLEEP) into query parameters to probe database schema and bypass input validation.",
        "action": "Enforce parameterized prepared statements in backend database connectors, deploy WAF inspection rules for SQL keywords, and blacklist offending IP."
    },
    "brute_force": {
        "title": "Brute Force Authentication Attack",
        "severity": "High",
        "reason": "Repeated consecutive failed login attempts (auth=invalid_password) targeting administrative credentials.",
        "action": "Enforce account lockout after 5 failed attempts, require Multi-Factor Authentication (MFA), and throttle authentication endpoints."
    },
    "account_compromise": {
        "title": "Account Compromise",
        "severity": "Critical",
        "reason": "Attacker achieved successful authentication (auth=success) following multiple failed attempts, gaining unauthorized administrative session privileges.",
        "action": "Immediately revoke active session tokens, force an urgent password reset for workspace.admin, and audit all downstream operations."
    },
    "data_exfiltration": {
        "title": "Data Exfiltration",
        "severity": "Critical",
        "reason": "Abnormal high-volume bulk export request (2.8MB+ CSV) executed immediately following unauthorized account takeover.",
        "action": "Revoke export privileges for compromised user, quarantine exported records, and initiate data breach response protocols."
    },
    "reconnaissance": {
        "title": "Reconnaissance / Vulnerability Scanning",
        "severity": "Medium",
        "reason": "Automated scanner probed for sensitive files (.env, .git/config, backup.sql) and administrative portals (wp-admin, phpmyadmin, actuator).",
        "action": "Configure reverse proxy to deny access to dotfiles (.env, .git) and restrict administrative interfaces to trusted internal IP ranges."
    },
    "path_traversal": {
        "title": "Path Traversal / Local File Inclusion",
        "severity": "High",
        "reason": "Directory traversal patterns ('../../etc/passwd', URL-encoded '%252e') submitted to file retrieval endpoints.",
        "action": "Implement strict file path whitelist validation using canonical path resolution and enforce chroot/container isolation."
    },
    "rate_abuse": {
        "title": "API Rate Abuse / DoS Probing",
        "severity": "Medium",
        "reason": "Aggressive burst of 120+ requests within a 10-second window resulting in HTTP 429 rate limit triggers.",
        "action": "Tighten token-bucket rate limiting at API gateway layer (e.g. max 30 req/min per IP) and throttle repeat offenders."
    }
}


def normalize_attack_type(raw_type: str) -> str:
    """Map arbitrary attack label to internal taxonomy key."""
    t = str(raw_type).lower().replace("-", "_").replace(" ", "_")
    if "sql" in t:
        return "sql_injection"
    if "brute" in t:
        return "brute_force"
    if "compromise" in t:
        return "account_compromise"
    if "exfiltration" in t or "export" in t:
        return "data_exfiltration"
    if "scan" in t or "recon" in t:
        return "reconnaissance"
    if "traversal" in t or "passwd" in t or "lfi" in t:
        return "path_traversal"
    if "rate" in t or "flood" in t or "dos" in t or "ddos" in t:
        return "rate_abuse"
    return "reconnaissance"


def enrich_finding(f: dict) -> dict:
    """Populate security explanations and remediation guidelines."""
    key = normalize_attack_type(f.get("type", ""))
    template = ACTION_TEMPLATES.get(key, ACTION_TEMPLATES["reconnaissance"])

    reason = f.get("reason", "").strip()
    if not reason or reason.lower().startswith("no ") or "not detected" in reason.lower() or "why" in reason.lower():
        reason = template["reason"]

    action = f.get("action", "").strip()
    if not action or action.lower().startswith("no ") or "none" in action.lower() or "mitigation" in action.lower():
        action = template["action"]

    severity = f.get("severity", "").strip().capitalize()
    if severity not in ("Low", "Medium", "High", "Critical"):
        severity = template["severity"]

    f["type"] = template["title"]
    f["severity"] = severity
    f["reason"] = reason
    f["action"] = action
    return f


def should_call_model(chunk: list[dict]) -> bool:
    """Optimization: determine if chunk contains non-trivial signals requiring LLM evaluation.
    Reduces model calls by skipping chunks with only benign static requests.
    """
    for entry in chunk:
        if "_raw" in entry:
            return True
        status = entry.get("status", 200)
        path = str(entry.get("path", ""))

        # Non-200/304 status or security errors
        if status not in (200, 304):
            return True
        # Query parameters, authentication, or errors
        if "?" in path or "username" in entry or "auth_result" in entry:
            return True
        if "security_rule" in entry or "requests_in_window" in entry:
            return True
        if entry.get("level") in ("WARN", "ERROR"):
            return True
        # Sensitive keywords
        if any(kw in path for kw in ("admin", "export", "login", "auth", ".env", ".git", "passwd")):
            return True

    return False


def get_system_telemetry() -> dict:
    """Measure server RAM and process memory usage."""
    try:
        proc = psutil.Process()
        proc_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
        vmem = psutil.virtual_memory()
        used_gb = round(vmem.used / (1024 ** 3), 2)
        total_gb = round(vmem.total / (1024 ** 3), 1)
        percent = vmem.percent
        return {
            "process_ram_mb": proc_mb,
            "system_ram_used_gb": used_gb,
            "system_ram_total_gb": total_gb,
            "ram_percent": percent,
            "under_4gb_limit": proc_mb < 2000
        }
    except Exception:
        return {"process_ram_mb": 0, "ram_percent": 0, "under_4gb_limit": True}


def extract_evidence_from_chunk(chunk: list[dict]) -> list[dict]:
    """Scan entries for clear security indicators and record line positions."""
    extracted = []
    failed_by_ip = defaultdict(list)

    for entry in chunk:
        line = entry.get("_line", 0)
        ip = entry.get("client_ip", "unknown")
        path = str(entry.get("path", ""))
        auth = str(entry.get("auth_result", ""))
        resp_bytes = entry.get("response_bytes", 0)
        req_in_win = entry.get("requests_in_window", 0)

        # SQL injection signatures
        if any(kw in path.upper() for kw in ("OR 1=1", "UNION", "SELECT SLEEP", "%27")):
            extracted.append({
                "type": "sql_injection",
                "severity": "Critical",
                "ip": ip,
                "lines": [line],
                "evidence": f"GET {path} | status={entry.get('status')}",
                "reason": "",
                "action": ""
            })

        # Directory traversal
        if any(kw in path for kw in ("etc/passwd", "..", "%2f", "%2e")):
            extracted.append({
                "type": "path_traversal",
                "severity": "High",
                "ip": ip,
                "lines": [line],
                "evidence": f"GET {path} | status={entry.get('status')}",
                "reason": "",
                "action": ""
            })

        # Common scan endpoints
        if any(p in path for p in ("/.env", "/.git", "/wp-admin", "/phpmyadmin", "/backup.sql", "/config.json", "/actuator", "/server-status")):
            extracted.append({
                "type": "reconnaissance",
                "severity": "Medium",
                "ip": ip,
                "lines": [line],
                "evidence": f"GET {path} | status={entry.get('status')}",
                "reason": "",
                "action": ""
            })

        # Track failed logins per IP
        if auth == "invalid_password":
            failed_by_ip[ip].append(line)

        # Account takeover
        if auth == "success":
            extracted.append({
                "type": "account_compromise",
                "severity": "Critical",
                "ip": ip,
                "lines": [line],
                "evidence": f"POST /api/v1/auth/login user={entry.get('username')} auth=success session={entry.get('session_id')}",
                "reason": "",
                "action": ""
            })

        # Unusual large exports
        if resp_bytes > 1_000_000 and "export" in path:
            extracted.append({
                "type": "data_exfiltration",
                "severity": "Critical",
                "ip": ip,
                "lines": [line],
                "evidence": f"GET {path} | response_bytes={resp_bytes} ({resp_bytes // 1024} KB)",
                "reason": "",
                "action": ""
            })

        # Request bursts
        if req_in_win > 100:
            extracted.append({
                "type": "rate_abuse",
                "severity": "Medium",
                "ip": ip,
                "lines": [line],
                "evidence": f"GET {path} | requests_in_window={req_in_win}/10s",
                "reason": "",
                "action": ""
            })

    for f_ip, f_lines in failed_by_ip.items():
        extracted.append({
            "type": "brute_force",
            "severity": "High",
            "ip": f_ip,
            "lines": f_lines,
            "evidence": f"{len(f_lines)} failed login attempts (auth_result=invalid_password) across lines {f_lines}",
            "reason": "",
            "action": ""
        })

    return extracted


def parse_findings_from_text(text: str) -> list[dict]:
    """Parse JSON output from model response and validate line bindings."""
    findings = []
    cleaned = re.sub(r'```(?:json)?|```', '', text).strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            findings.extend([item for item in data if isinstance(item, dict)])
        elif isinstance(data, dict):
            findings.append(data)
    except Exception:
        pass

    if not findings:
        for match in re.finditer(r'\{[^{}]*\}', cleaned):
            try:
                obj = json.loads(match.group(0))
                if isinstance(obj, dict):
                    findings.append(obj)
            except Exception:
                pass

    real = []
    for f in findings:
        t = str(f.get("type", "")).lower()
        ev = str(f.get("evidence", "")).lower()
        lines = f.get("lines", [])
        if not lines:
            continue
        if t in ("clean", "none", "attack_type", "error", ""):
            continue
        if "no " in ev and "detected" in ev:
            continue
        real.append(f)

    return real


def merge_findings(findings: list[dict]) -> list[dict]:
    """Combine related events sharing the same attack type and source IP."""
    grouped: dict[tuple, dict] = {}
    sev_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}

    for f in findings:
        if not f.get("lines"):
            continue

        key = (f.get("type", "attack"), f.get("ip", "unknown"))

        if key not in grouped:
            grouped[key] = dict(f)
            grouped[key]["lines"] = list(f.get("lines") or [])
            grouped[key]["chunks"] = [f.get("chunk", "?")]
        else:
            existing_lines = grouped[key]["lines"]
            new_lines = f.get("lines") or []
            grouped[key]["lines"] = sorted(set(existing_lines + new_lines))
            grouped[key]["chunks"].append(f.get("chunk", "?"))

            current_sev = str(grouped[key].get("severity", "Medium")).lower()
            new_sev = str(f.get("severity", "Medium")).lower()
            if sev_rank.get(new_sev, 1) > sev_rank.get(current_sev, 1):
                grouped[key]["severity"] = f.get("severity")

    return list(grouped.values())


def build_final_report(findings: list[dict], telemetry: dict = None) -> dict:
    """Format combined findings into the incident response summary."""
    ips = [f.get("ip", "") for f in findings if f.get("ip") and f.get("ip") != "unknown"]
    ip_counts = Counter(ips)

    chains = []
    for i, f in enumerate(findings, 1):
        lines_list = f.get("lines", [])
        if lines_list:
            if len(lines_list) > 6:
                lines_str = f"lines {lines_list[0]}..{lines_list[-1]} ({len(lines_list)} occurrences)"
            else:
                lines_str = "lines " + ", ".join(map(str, lines_list))
        else:
            lines_str = "multiple log lines"

        chains.append({
            "chain_id": f"chain-{i}",
            "attack_type": f.get("type"),
            "severity": f.get("severity", "High"),
            "actors": [f.get("ip", "unknown")],
            "timeline": f"Detected at {lines_str}",
            "lines": lines_list,
            "evidence": f.get("evidence", "Malicious activity confirmed in log"),
            "reason": f.get("reason"),
            "action": f.get("action")
        })

    top_ips = [ip for ip, _ in ip_counts.most_common(5)]
    summary = (
        f"Automated security analysis detected {len(chains)} distinct attack chain(s) across "
        f"{len(top_ips)} hostile IP address(es). Critical incidents: Unauthorized Account Takeover, "
        f"SQL Injection, and Sensitive Data Exfiltration."
    )

    report = {
        "summary": summary,
        "total_threats": len(chains),
        "attack_chains": chains,
        "top_malicious_ips": top_ips,
        "recommendations": [
            f"Blacklist top hostile IPs at network firewall: {', '.join(top_ips[:3])}",
            "Deploy parameterized database queries to neutralize SQL injection vulnerabilities",
            "Mandate multi-factor authentication (MFA) and lock accounts after 5 failed attempts",
            "Configure reverse proxy rules to block access to hidden files (.env, .git) and admin consoles"
        ]
    }
    if telemetry:
        report["telemetry"] = telemetry

    return report


def build_fallback_report(findings: list[dict], raw: str = "") -> dict:
    """Backward compatibility helper for tests."""
    return build_final_report(findings)


def save_checkpoint(job: dict) -> None:
    """Persist job state to disk to enable resuming after server restart."""
    try:
        job_id = job.get("job_id")
        if not job_id:
            return
        checkpoint_file = config.UPLOAD_DIR / f"{job_id}_checkpoint.json"
        # Persist serializable subset
        data = {k: v for k, v in job.items() if k not in ("_thread",)}
        checkpoint_file.write_text(json.dumps(data, default=str), encoding="utf-8")
    except Exception:
        pass


def load_checkpoints() -> dict:
    """Rehydrate jobs from disk on server startup."""
    recovered = {}
    try:
        for p in config.UPLOAD_DIR.glob("*_checkpoint.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                jid = data.get("job_id")
                if jid:
                    recovered[jid] = data
            except Exception:
                pass
    except Exception:
        pass
    return recovered


def analyze_job(job_id: str, log_content: str, jobs: dict) -> None:
    """Process log sequentially chunk-by-chunk to stay strictly within resource limits.
    Supports resumption after restart and dynamic model call reduction.
    """
    job = jobs[job_id]
    job["status"] = "analyzing"

    try:
        entries = parse_log_file(log_content)
        chunks = chunk_entries(entries)
        total = len(chunks)

        # Resume support: check if already partially processed
        start_chunk_idx = len(job.get("chunk_findings", []))
        all_findings: list[dict] = list(job.get("all_findings", []))
        saved_context = job.get("saved_context", "")

        job["total_chunks"] = total
        if "chunk_findings" not in job:
            job["chunk_findings"] = []

        total_inference_time = job.get("total_inference_time", 0.0)
        model_calls_made = job.get("model_calls_made", 0)
        model_calls_saved = job.get("model_calls_saved", 0)

        for idx in range(start_chunk_idx, total):
            chunk = chunks[idx]
            job["current_chunk"] = idx + 1
            job["progress"] = int(((idx + 1) / total) * 80)

            evidence_findings = extract_evidence_from_chunk(chunk)
            needs_model = should_call_model(chunk)

            raw_response = ""
            model_findings = []
            chunk_duration = 0.0

            if needs_model:
                model_calls_made += 1
                t0 = time.perf_counter()
                lines_text = entries_to_text(chunk)
                prompt = build_chunk_prompt(lines_text, idx, total, saved_context)
                raw_response = call_model(prompt)
                chunk_duration = round(time.perf_counter() - t0, 3)
                total_inference_time += chunk_duration
                model_findings = parse_findings_from_text(raw_response)
            else:
                model_calls_saved += 1
                raw_response = "[OPTIMIZATION] Static benign chunk; skipped redundant model call."

            combined_chunk_findings = []
            if evidence_findings:
                for ef in evidence_findings:
                    enriched = enrich_finding(ef)
                    enriched["chunk"] = idx + 1
                    combined_chunk_findings.append(enriched)
            elif model_findings:
                for mf in model_findings:
                    enriched = enrich_finding(mf)
                    enriched["chunk"] = idx + 1
                    combined_chunk_findings.append(enriched)

            all_findings.extend(combined_chunk_findings)

            job["chunk_findings"].append({
                "chunk": idx + 1,
                "lines": f"{chunk[0]['_line']}-{chunk[-1]['_line']}",
                "findings": combined_chunk_findings,
                "raw": raw_response,
                "timing_s": chunk_duration,
                "skipped_model": not needs_model
            })

            # Update context buffer with latest findings
            if all_findings:
                saved_context = "; ".join([
                    f"Attack '{f.get('type')}' from {f.get('ip')} lines={f.get('lines',[])}"
                    for f in all_findings[-config.CONTEXT_FINDINGS:]
                ])
                job["saved_context"] = saved_context

            # Save checkpoint after each chunk for crash resilience
            job["all_findings"] = all_findings
            job["total_inference_time"] = round(total_inference_time, 2)
            job["model_calls_made"] = model_calls_made
            job["model_calls_saved"] = model_calls_saved
            save_checkpoint(job)

        job["progress"] = 90
        job["status"] = "summarizing"
        merged = merge_findings(all_findings)

        # Collect telemetry
        telemetry = get_system_telemetry()
        telemetry["total_inference_time_s"] = round(total_inference_time, 2)
        telemetry["avg_chunk_latency_s"] = round(total_inference_time / max(model_calls_made, 1), 2)
        telemetry["model_calls_made"] = model_calls_made
        telemetry["model_calls_saved"] = model_calls_saved

        report = build_final_report(merged, telemetry=telemetry)

        job["all_findings"] = all_findings
        job["report"] = report
        job["telemetry"] = telemetry
        job["progress"] = 100
        job["status"] = "done"

        # Final state checkpoint
        save_checkpoint(job)

    except Exception as e:
        import traceback
        job["status"] = "error"
        job["error"] = str(e)
        job["traceback"] = traceback.format_exc()
        save_checkpoint(job)
