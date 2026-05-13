import json
from mcp import mcp
from nodes import get_stats


def traffic_stats() -> str:
    stats = get_stats()
    if not stats:
        return "❌ Не удалось получить статистику"

    u = stats.get("users", {})
    n = stats.get("nodes", {})
    node_list = n.get("list", [])

    total_rx = sum(nd.get("traffic", {}).get("rx", 0) for nd in node_list)
    total_tx = sum(nd.get("traffic", {}).get("tx", 0) for nd in node_list)
    rx_gb = round(total_rx / 1024 ** 3, 2)
    tx_gb = round(total_tx / 1024 ** 3, 2)

    last_sync = stats.get("lastSync", "?")[:19].replace("T", " ")

    lines = [
        "📈  TRAFFIC OVERVIEW",
        "─" * 26,
        f"👤  Пользователи:  {u.get('enabled', 0)} активных / {u.get('total', 0)} всего",
        f"📡  Ноды:          {n.get('online', 0)}/{n.get('total', 0)} онлайн",
        f"👥  Сейчас онлайн: {stats.get('onlineUsers', 0)} клиентов",
        "",
        "─" * 26,
        f"⬇  Загрузка:   {rx_gb} GB",
        f"⬆  Отдача:     {tx_gb} GB",
        f"📦  Суммарно:   {round(rx_gb + tx_gb, 2)} GB",
        "─" * 26,
        f"🕐  Последний синк: {last_sync}",
    ]
    return "\n".join(lines)


def node_stats_by_pattern(pattern: str) -> str:
    stats = get_stats()
    node_list = stats.get("nodes", {}).get("list", [])
    filtered = [n for n in node_list if pattern.lower() in n.get("name", "").lower()]

    if not filtered:
        return f"❌ Ноды не найдены: {pattern}"

    flag = "🇫🇮" if pattern.lower() == "fi" else "🇩🇪"
    lines = [f"{flag}  STATS — {pattern.upper()}", "─" * 24]

    for node in filtered:
        name    = node.get("name", "?")
        status  = node.get("status", "offline")
        clients = node.get("online", 0)
        t       = node.get("traffic", {})
        rx = round(t.get("rx", 0) / 1024 ** 3, 2)
        tx = round(t.get("tx", 0) / 1024 ** 3, 2)
        em = "🟢" if status == "online" else "🔴"
        lines += [
            f"\n{em} {name}",
            f"   👥 {clients} clients",
            f"   ⬇ {rx} GB   ⬆ {tx} GB",
        ]

    return "\n".join(lines)


def online_clients() -> str:
    stats = get_stats()
    node_list    = stats.get("nodes", {}).get("list", [])
    total_online = stats.get("onlineUsers", 0)

    if not node_list:
        return "❌ Нет данных"

    lines = ["👥  ONLINE CLIENTS", "─" * 24]
    for node in node_list:
        name    = node.get("name", "?")
        clients = node.get("online", 0)
        status  = node.get("status", "offline")
        if status == "online":
            bar = "▓" * min(clients, 20)
            lines.append(f"  🟢 {name}: {clients}  {bar}")
        else:
            lines.append(f"  🔴 {name}: offline")

    lines += ["─" * 24, f"🔢  Всего онлайн: {total_online}"]
    return "\n".join(lines)


def top_users_by_traffic(limit: int = 10) -> str:
    data = mcp("query", {"resource": "users"})
    try:
        raw   = data["result"]["content"][0]["text"]
        users = json.loads(raw)["users"]
    except Exception:
        return "❌ Не удалось получить список пользователей"

    def total(u):
        t = u.get("traffic", {})
        return t.get("rx", 0) + t.get("tx", 0)

    sorted_users = sorted(users, key=total, reverse=True)[:limit]
    medals = ["🥇", "🥈", "🥉"]
    lines  = [f"🏆  TOP {limit} BY TRAFFIC", "─" * 24]

    for i, u in enumerate(sorted_users, 1):
        name = u.get("username", "?")
        gb   = round(total(u) / 1024 ** 3, 2)
        em   = "🟢" if u.get("enabled", True) else "🔴"
        rank = medals[i - 1] if i <= 3 else f"{i}."
        lines.append(f"  {rank} {em} {name} — {gb} GB")

    return "\n".join(lines)


def get_nodes_for_chart() -> list[dict]:
    stats = get_stats()
    return stats.get("nodes", {}).get("list", [])
