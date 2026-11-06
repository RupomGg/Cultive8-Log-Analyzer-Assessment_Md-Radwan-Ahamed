import json
import urllib.parse
import config


def parse_log_file(content: str) -> list[dict]:
    """Parse log content into entry dicts with 1-based line numbers."""
    entries = []
    for i, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            entry["_line"] = i
            entries.append(entry)
        except json.JSONDecodeError:
            entries.append({"_line": i, "_raw": line})
    return entries


def chunk_entries(entries: list[dict], chunk_size: int = None) -> list[list[dict]]:
    """Partition entries into size-bounded chunks."""
    size = chunk_size or config.CHUNK_LINES
    return [entries[i:i + size] for i in range(0, len(entries), size)]


def entries_to_text(chunk: list[dict]) -> str:
    """Serialize chunk entries into normalized, readable key-value lines for LLM context."""
    lines = []
    for e in chunk:
        if "_raw" in e:
            lines.append(f"Line {e['_line']}: {e['_raw']}")
            continue

        line_no = e.get("_line", "?")
        ip = e.get("client_ip", "unknown")
        method = e.get("method", "")
        raw_path = e.get("path", "")
        path = urllib.parse.unquote(raw_path) if raw_path else ""
        status = e.get("status", "")

        parts = [f"Line {line_no}: IP={ip}"]
        if method or path:
            parts.append(f"{method} {path}")
        if status:
            parts.append(f"status={status}")
        if "username" in e:
            parts.append(f"user={e['username']}")
        if "auth_result" in e:
            parts.append(f"auth={e['auth_result']}")
        if "security_rule" in e:
            parts.append(f"sec_rule={e['security_rule']}")
        if "requests_in_window" in e:
            parts.append(f"req_in_window={e['requests_in_window']}/{e.get('window_seconds')}s")
        if "message" in e:
            parts.append(f"msg=\"{e['message']}\"")
        if "exception" in e:
            parts.append(f"exception={e['exception']}")

        lines.append(" | ".join(parts))
    return "\n".join(lines)
