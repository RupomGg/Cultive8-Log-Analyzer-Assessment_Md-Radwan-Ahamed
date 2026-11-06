"""Prompt construction for chunk analysis and summary consolidation."""


def build_chunk_prompt(lines_text: str, chunk_idx: int,
                       total_chunks: int, saved_context: str) -> str:
    """Build the analysis prompt for a single log chunk."""
    ctx = f"\nPREVIOUS FINDINGS TO LINK:\n{saved_context}\n" if saved_context else ""

    return f"""You are a cybersecurity log analyst. Examine these server logs (part {chunk_idx+1}/{total_chunks}).
{ctx}
LOGS:
{lines_text}

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
{{"type":"<attack_type>","severity":"Low|Medium|High|Critical","ip":"<ip>","lines":[<line_numbers>],"evidence":"<quoted path or message>","reason":"<why malicious>","action":"<recommended action>"}}

Respond ONLY with the JSON array: ###"""


def build_summary_prompt(findings_text: str) -> str:
    """Build the consolidation prompt to link events into attack chains."""
    return f"""You are a senior security lead. Combine these raw security events into ONE cohesive executive incident report.

EVENTS DETECTED:
{findings_text}

Merge related events into attack chains (e.g., link brute force attempts to subsequent successful logins and data exports).
Output a JSON object with this exact structure:
{{
  "summary": "2-3 sentence executive summary of overall incidents",
  "total_threats": <number_of_distinct_attacks>,
  "attack_chains": [
    {{
      "chain_id": "chain-1",
      "attack_type": "...",
      "severity": "Critical|High|Medium|Low",
      "actors": ["ip1"],
      "timeline": "chronological sequence of events",
      "lines": [line_numbers],
      "evidence": "quoted evidence",
      "reason": "why this is an attack",
      "action": "immediate mitigation"
    }}
  ],
  "top_malicious_ips": ["ip1", "ip2"],
  "recommendations": ["rec1", "rec2", "rec3"]
}}
Respond ONLY with the JSON object: ###"""
