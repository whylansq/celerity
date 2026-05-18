from mcp import api_get_nodes, api_ssh


def get_nodes() -> list[dict]:
    return api_get_nodes()


def get_stats() -> dict:
    return {}


def format_status() -> str:
    nodes = get_nodes()
    if not nodes:
        return "❌ Ноды недоступны — проверь API"

    lines = ["🖥  NODE STATUS\n" + "─" * 28]
    online_count = 0

    for node in nodes:
        status  = node.get("status", "offline")
        name    = node.get("name", "unknown")
        ntype   = node.get("type", "?")
        ip      = node.get("ip", "?")
        port    = node.get("port", "?")
        clients = node.get("onlineUsers", 0)
        em      = "🟢" if status == "online" else "🔴"
        tag     = "⚡ HYS" if ntype == "hysteria" else "🌐 VLS"
        t       = node.get("traffic", {})
        rx_gb   = round(t.get("rx", 0) / 1024 ** 3, 2)
        tx_gb   = round(t.get("tx", 0) / 1024 ** 3, 2)

        lines.append(
            f"\n{em} {name}  [{tag}]  {'online' if status == 'online' else 'OFFLINE'}\n"
            f"   📍 {ip}:{port}\n"
            f"   👥 {clients} clients  ⬇ {rx_gb} GB  ⬆ {tx_gb} GB"
        )
        if status == "online":
            online_count += 1

    total  = len(nodes)
    health = "✅ Все работают" if online_count == total else f"⚠️ {online_count}/{total} онлайн"
    lines.append("\n" + "─" * 28 + f"\n{health}")
    return "\n".join(lines)


def restart_node(node_id: str) -> dict:
    _, err = api_ssh(node_id,
        "systemctl restart hysteria-server 2>/dev/null; "
        "systemctl restart xray 2>/dev/null; true"
    )
    return {"error": err} if err else {"ok": True}


def restart_service(node_id: str, service: str) -> dict:
    commands = {
        "hysteria": "systemctl restart hysteria-server 2>/dev/null; true",
        "vless":    "systemctl restart xray 2>/dev/null; true",
        "all":      "systemctl restart hysteria-server 2>/dev/null; systemctl restart xray 2>/dev/null; true",
    }
    _, err = api_ssh(node_id, commands.get(service, commands["all"]))
    return {"error": err} if err else {"ok": True}


def restart_by_name(name_pattern: str, service: str = "all") -> str:
    nodes   = get_nodes()
    targets = [n for n in nodes if name_pattern.lower() in n.get("name", "").lower()]
    if not targets:
        return f"❌ Ноды не найдены: «{name_pattern}»"

    ok_list, err_list = [], []
    for node in targets:
        r = restart_service(node["_id"], service)
        (err_list if "error" in r else ok_list).append(node["name"])

    parts = []
    if ok_list:
        parts.append("✅ Перезапущены:\n" + "\n".join(f"  • {n}" for n in ok_list))
    if err_list:
        parts.append("❌ Ошибка:\n" + "\n".join(f"  • {n}" for n in err_list))
    return "\n".join(parts)


def restart_all_nodes() -> str:
    nodes = get_nodes()
    if not nodes:
        return "❌ Ноды не найдены"
    lines = ["🔄 ПЕРЕЗАПУСК ВСЕХ НОД\n" + "─" * 24]
    for node in nodes:
        r  = restart_node(node["_id"])
        em = "✅" if "ok" in r else "❌"
        lines.append(f"{em} {node['name']}")
    return "\n".join(lines)


def panic_restart() -> str:
    nodes = get_nodes()
    if not nodes:
        return "❌ Ноды не найдены"
    lines = ["💀 PANIC RESTART\n" + "─" * 24]
    for node in nodes:
        cmd = (
            "systemctl stop hysteria-server 2>/dev/null; "
            "systemctl stop xray 2>/dev/null; "
            "sleep 2; "
            "systemctl start hysteria-server 2>/dev/null; "
            "systemctl start xray 2>/dev/null; true"
        )
        _, err = api_ssh(node["_id"], cmd)
        lines.append(f"{'✅' if not err else '❌'} {node['name']}")
    lines.append("\n🕐 Все сервисы остановлены → 2s → запущены")
    return "\n".join(lines)


def get_nodes_inline_list() -> list[tuple]:
    return [(n["_id"], n.get("name", "?"), n.get("type", "hysteria")) for n in get_nodes()]
