"""
Server monitoring через API панели.
SSH-мониторинг убран — панель его не поддерживает через API.
Используем данные нод из /api/nodes.
"""

from mcp import api_get_nodes


def get_unique_server_nodes() -> list[dict]:
    """Возвращает уникальные серверы (по IP)."""
    nodes = api_get_nodes()
    seen: dict[str, dict] = {}
    for n in nodes:
        ip = n.get("ip", "")
        if ip and ip not in seen:
            seen[ip] = n
    return list(seen.values())


def format_server_stats() -> str:
    """Статус серверов из API панели (без SSH)."""
    nodes = api_get_nodes()
    if not nodes:
        return "❌ Ноды не найдены"

    # Группируем по IP
    servers: dict[str, list[dict]] = {}
    for n in nodes:
        ip = n.get("ip", "?")
        servers.setdefault(ip, []).append(n)

    text = "🖥 SERVER STATUS\n\n"
    for ip, node_list in servers.items():\
        # Определяем флаг по имени нод
        names = [n.get("name", "") for n in node_list]
        flag  = "🇫🇮" if any("fi" in nm.lower() for nm in names) else "🇩🇪"
        text += f"{flag} {ip}\n"

        for node in node_list:
            em     = "🟢" if node.get("status") == "online" else "🔴"
            name   = node.get("name", "?")
            ntype  = "HYS" if node.get("type") == "hysteria" else "VLS"
            online = node.get("onlineUsers", 0)
            t      = node.get("traffic", {})
            rx     = round(t.get("rx", 0) / 1024 ** 3, 2)
            tx     = round(t.get("tx", 0) / 1024 ** 3, 2)
            text  += f"   {em} {name} [{ntype}] 👥{online} ⬇{rx}GB ⬆{tx}GB\n"

        text += "\n"

    text += "ℹ️ CPU/RAM/Disk доступны только через веб-панель (SSH Terminal)"
    return text.strip()


def ssh_command(node_id: str, cmd: str) -> str:
    return "❌ SSH через API недоступен. Используй SSH Terminal в веб-панели."


def reboot_server(node_id: str) -> tuple[bool, str]:
    return False, "❌ Ребут через API недоступен. Используй SSH Terminal в веб-панели."


def get_disk_usage_pct(node_id: str) -> float | None:
    return None


def get_cpu_pct(node_id: str) -> float | None:
    return None
