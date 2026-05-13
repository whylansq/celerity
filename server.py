"""
SSH-based physical server monitoring.
Groups nodes by IP so each real server is queried only once.
"""

import json
from mcp import mcp
from nodes import get_nodes

# ── SSH helpers ────────────────────────────────────────────────────────────────

_STATS_CMD = r"""
cpu=$(top -bn1 2>/dev/null | grep 'Cpu(s)' | \
  awk '{for(i=1;i<=NF;i++) if($(i+1)~/id/) {gsub(/[^0-9.]/,"",$i); printf "%.1f", 100-$i; exit}}'); \
mem=$(free -m 2>/dev/null | awk '/^Mem:/{printf "%.1f/%.1fGB %.0f%%", $3/1024, $2/1024, $3/$2*100}'); \
disk=$(df -h / 2>/dev/null | awk 'NR==2{printf "%s/%s %s", $3, $2, $5}'); \
load=$(uptime 2>/dev/null | awk -F'load average: ' '{print $2}'); \
up=$(uptime -p 2>/dev/null | sed 's/up //' || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}'); \
echo "CPU:${cpu:-?}%|MEM:${mem:-?}|DISK:${disk:-?}|LOAD:${load:-?}|UP:${up:-?}"
"""


def _ssh(node_id: str, cmd: str) -> tuple[str | None, str | None]:
    r = mcp("execute_ssh", {"nodeId": node_id, "command": cmd})
    try:
        out = r["result"]["content"][0]["text"].strip()
        return out, None
    except Exception:
        return None, str(r.get("error", "unknown error"))


def _parse_stats(raw: str) -> dict:
    """Parse the stats one-liner output into a dict."""
    result = {}
    for part in raw.split("|"):
        if ":" in part:
            k, _, v = part.partition(":")
            result[k.strip()] = v.strip()
    return result


# ── Public API ─────────────────────────────────────────────────────────────────

def get_unique_server_nodes() -> list[dict]:
    """Return one node per unique physical IP (to avoid querying same box twice)."""
    nodes = get_nodes()
    seen: dict[str, dict] = {}
    for n in nodes:
        ip = n.get("ip", "")
        if ip and ip not in seen:
            seen[ip] = n
    return list(seen.values())


def get_server_stats_raw(node_id: str) -> tuple[dict | None, str | None]:
    out, err = _ssh(node_id, _STATS_CMD)
    if err or not out:
        return None, err
    return _parse_stats(out), None


def format_server_stats() -> str:
    servers = get_unique_server_nodes()
    if not servers:
        return "❌ No nodes found"

    text = "🖥 SERVER RESOURCES\n\n"
    for node in servers:
        node_id = node["_id"]
        ip = node.get("ip", "?")
        # figure out flag from node names that share this IP
        all_nodes = get_nodes()
        names = [n.get("name", "") for n in all_nodes if n.get("ip") == ip]
        flag = "🇫🇮" if any("fi" in nm.lower() for nm in names) else "🇩🇪"

        stats, err = get_server_stats_raw(node_id)
        if err or not stats:
            text += f"{flag} {ip}\n   ❌ SSH error: {err}\n\n"
            continue

        cpu_str = stats.get("CPU", "?")
        mem_str = stats.get("MEM", "?")
        disk_str = stats.get("DISK", "?")
        load_str = stats.get("LOAD", "?")
        up_str = stats.get("UP", "?")

        # Colour indicators
        try:
            cpu_val = float(cpu_str.replace("%", ""))
            cpu_em = "🔴" if cpu_val > 85 else ("🟡" if cpu_val > 60 else "🟢")
        except Exception:
            cpu_em = "⚪"

        text += (
            f"{flag} {ip}\n"
            f"   {cpu_em} CPU: {cpu_str}%\n"
            f"   💾 RAM: {mem_str}\n"
            f"   💿 Disk: {disk_str}\n"
            f"   📊 Load: {load_str}\n"
            f"   ⏱ Up: {up_str}\n\n"
        )

    return text.strip()


def ssh_command(node_id: str, cmd: str) -> str:
    out, err = _ssh(node_id, cmd)
    if err:
        return f"❌ SSH error: {err}"
    return out or "(no output)"


def reboot_server(node_id: str) -> tuple[bool, str]:
    _, err = _ssh(node_id, "shutdown -r +0 2>/dev/null || reboot")
    if err:
        return False, f"❌ Reboot failed: {err}"
    return True, "♻️ Reboot command sent"


def get_disk_usage_pct(node_id: str) -> float | None:
    """Return disk usage % for / partition, or None on error."""
    out, err = _ssh(node_id, "df / | tail -1 | awk '{print $5}' | tr -d '%'")
    if err or not out:
        return None
    try:
        return float(out.strip())
    except Exception:
        return None


def get_cpu_pct(node_id: str) -> float | None:
    out, err = _ssh(
        node_id,
        r"top -bn1 | grep 'Cpu(s)' | awk '{for(i=1;i<=NF;i++) if($(i+1)~/id/) "
        r"{gsub(/[^0-9.]/,\"\",$i); printf \"%.1f\", 100-$i; exit}}'",
    )
    if err or not out:
        return None
    try:
        return float(out.strip())
    except Exception:
        return None
