import os
import time
from mcp import mcp
from nodes import get_nodes


def _ssh(node_id, cmd):
    r = mcp("execute_ssh", {"nodeId": node_id, "command": cmd})
    try:
        return r["result"]["content"][0]["text"], None
    except Exception as e:
        return None, str(r.get("error", e))


def backup_node(node_id, node_name, node_type, paths):
    if node_type == "hysteria":
        cfg = paths.get("config", "/etc/hysteria/config.yaml")
        cmd = f"cat {cfg}"
    else:
        cmd = "cat /usr/local/etc/xray/config.json 2>/dev/null || cat /etc/xray/config.json 2>/dev/null"

    content, err = _ssh(node_id, cmd)
    if err or not content:
        return None, f"SSH error: {err}"

    safe_name = node_name.replace(" ", "_")
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{safe_name}_{ts}.cfg"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return filename, None


def backup_all():
    nodes = get_nodes()
    if not nodes:
        return [], "❌ No nodes found"

    files = []
    lines = []
    for node in nodes:
        node_id = node["_id"]
        name = node.get("name", "?")
        ntype = node.get("type", "hysteria")
        paths = node.get("paths", {})

        path, err = backup_node(node_id, name, ntype, paths)
        if path:
            files.append(path)
            lines.append(f"✅ {name} → {path}")
        else:
            lines.append(f"❌ {name}: {err}")

    return files, "\n".join(lines)


def reinstall_node(node_id, node_type):
    if node_type == "hysteria":
        cmd = (
            "systemctl stop hysteria-server 2>/dev/null; "
            "bash <(curl -fsSL https://get.hy2.sh/) --remove 2>/dev/null || true; "
            "bash <(curl -fsSL https://get.hy2.sh/) 2>&1 | tail -8"
        )
    else:
        cmd = (
            "systemctl stop xray 2>/dev/null; "
            "bash <(curl -fsSL https://github.com/XTLS/Xray-install/raw/main/install-release.sh)"
            " @ remove 2>/dev/null || true; "
            "bash <(curl -fsSL https://github.com/XTLS/Xray-install/raw/main/install-release.sh)"
            " @ install 2>&1 | tail -8"
        )

    output, err = _ssh(node_id, cmd)
    if err:
        return False, f"❌ SSH error: {err}"

    return True, f"🔧 Reinstall output:\n```\n{(output or '')[:600]}\n```"


def cleanup_backup(filename):
    try:
        if filename and os.path.exists(filename):
            os.remove(filename)
    except Exception:
        pass
