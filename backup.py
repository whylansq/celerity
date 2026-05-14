import os
import time
from mcp import api_ssh
from mcp import api_get_nodes
from events import log_event


def backup_node(node_id, node_name, node_type, paths):
    if node_type == "hysteria":
        cfg = paths.get("config", "/etc/hysteria/config.yaml")
        cmd = f"cat {cfg}"
    else:
        cmd = "cat /usr/local/etc/xray/config.json 2>/dev/null || cat /etc/xray/config.json 2>/dev/null"

    content, err = api_ssh(node_id, cmd)
    if err or not content:
        log_event("ssh_error", node_name, f"backup: {err}")
        return None, f"SSH error: {err}"

    safe_name = node_name.replace(" ", "_")
    ts        = time.strftime("%Y%m%d_%H%M%S")
    filename  = f"/tmp/backup_{safe_name}_{ts}.cfg"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    log_event("backup", node_name, filename)
    return filename, None


def backup_all():
    nodes = api_get_nodes()
    if not nodes:
        return [], "❌ No nodes found"

    files = []
    lines = []
    for node in nodes:
        node_id = node["_id"]
        name    = node.get("name", "?")
        ntype   = node.get("type", "hysteria")
        paths   = node.get("paths", {})

        path, err = backup_node(node_id, name, ntype, paths)
        if path:
            files.append(path)
            lines.append(f"✅ {name} → {os.path.basename(path)}")
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

    output, err = api_ssh(node_id, cmd)
    if err:
        log_event("ssh_error", node_id, f"reinstall: {err}")
        return False, f"❌ SSH error: {err}"

    return True, f"🔧 Reinstall output:\n```\n{(output or '')[:600]}\n```"


def cleanup_backup(filename):
    try:
        if filename and os.path.exists(filename):
            os.remove(filename)
    except Exception:
        pass
