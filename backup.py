"""
Backup через встроенный API панели.
SSH-бэкап убран — панель его не поддерживает через API.
"""

import os
import time
from mcp import _get, api_get_nodes


def backup_all():
    """
    Панель поддерживает бэкап через веб-интерфейс.
    Через API прямого эндпоинта скачивания бэкапа нет.
    Возвращаем информацию о нодах вместо конфигов.
    """
    nodes = api_get_nodes()
    if not nodes:
        return [], "❌ Ноды не найдены"

    lines = ["💾 BACKUP INFO\n"]
    lines.append("ℹ️ SSH-бэкап конфигов недоступен через API панели.\n")
    lines.append("Используй встроенный бэкап в веб-панели:\nSettings → Backups → Manual Backup\n")
    lines.append(f"📡 Текущие ноды ({len(nodes)}):")

    for node in nodes:
        em     = "🟢" if node.get("status") == "online" else "🔴"
        name   = node.get("name", "?")
        ntype  = node.get("type", "?")
        sync   = node.get("lastSync", "")[:19].replace("T", " ") if node.get("lastSync") else "—"
        lines.append(f"  {em} {name} ({ntype}) — последний синк: {sync}")

    return [], "\n".join(lines)


def reinstall_node(node_id: str, node_type: str):
    """Переустановка через SSH убрана — используй Auto Setup в веб-панели."""
    return False, (
        "ℹ️ Переустановка через SSH недоступна через API.\n\n"
        "Используй Auto Setup в веб-панели:\n"
        "Nodes → выбери ноду → ⚙️ Auto Setup"
    )


def cleanup_backup(filename: str):
    try:
        if filename and os.path.exists(filename):
            os.remove(filename)
    except Exception:
        pass
