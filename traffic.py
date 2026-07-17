from mcp import api_get_nodes, api_get_users


def traffic_stats() -> str:
    nodes = api_get_nodes()
    if not nodes:
        return "❌ Не удалось получить статистику"

    users        = api_get_users()
    online       = sum(1 for n in nodes if n.get("status") == "online")
    active_users = sum(1 for u in users if u.get("enabled", True))
    online_users = sum(n.get("onlineUsers", 0) for n in nodes)
    total_rx     = sum(n.get("traffic", {}).get("rx", 0) for n in nodes)
    total_tx     = sum(n.get("traffic", {}).get("tx", 0) for n in nodes)
    rx_gb        = round(total_rx / 1024 ** 3, 2)
    tx_gb        = round(total_tx / 1024 ** 3, 2)

    lines = [
        "📈  TRAFFIC OVERVIEW",
        "─" * 26,
        f"👤  Пользователи:  {active_users} активных / {len(users)} всего",
        f"📡  Ноды:          {online}/{len(nodes)} онлайн",
        f"👥  Сейчас онлайн: {online_users} клиентов",
        "",
        "─" * 26,
        f"⬇  Загрузка:   {rx_gb} GB",
        f"⬆  Отдача:     {tx_gb} GB",
        f"📦  Суммарно:   {round(rx_gb + tx_gb, 2)} GB",
    ]
    return "\n".join(lines)


def node_stats_by_pattern(pattern: str) -> str:
    nodes    = api_get_nodes()
    filtered = [n for n in nodes if pattern.lower() in n.get("name", "").lower()]
    if not filtered:
        return f"❌ Ноды не найдены: {pattern}"

    flag  = "🇫🇮" if pattern.lower() == "fi" else ("🇩🇪" if pattern.lower() in ("ge", "de") else "📡")
    lines = [f"{flag}  STATS — {pattern.upper()}", "─" * 24]
    for node in filtered:
        name    = node.get("name", "?")
        status  = node.get("status", "offline")
        clients = node.get("onlineUsers", 0)
        t       = node.get("traffic", {})
        rx = round(t.get("rx", 0) / 1024 ** 3, 2)
        tx = round(t.get("tx", 0) / 1024 ** 3, 2)
        em = "🟢" if status == "online" else "🔴"
        lines += [f"\n{em} {name}", f"   👥 {clients} clients", f"   ⬇ {rx} GB   ⬆ {tx} GB"]
    return "\n".join(lines)


def node_stats_dynamic(node_name: str) -> str:
    return node_stats_by_pattern(node_name)


def online_clients() -> str:
    nodes        = api_get_nodes()
    total_online = sum(n.get("onlineUsers", 0) for n in nodes)
    if not nodes:
        return "❌ Нет данных"

    lines = ["👥  ONLINE CLIENTS", "─" * 24]
    for node in nodes:
        name    = node.get("name", "?")
        clients = node.get("onlineUsers", 0)
        status  = node.get("status", "offline")
        if status == "online":
            bar = "▓" * min(clients, 20)
            lines.append(f"  🟢 {name}: {clients}  {bar}")
        else:
            lines.append(f"  🔴 {name}: offline")

    lines += ["─" * 24, f"🔢  Всего онлайн: {total_online}"]
    return "\n".join(lines)


def top_users_by_traffic(limit: int = 10) -> str:
    users = api_get_users()
    if not users:
        return "❌ Не удалось получить список пользователей"

    def total(u):
        t = u.get("traffic", {})
        return t.get("rx", 0) + t.get("tx", 0)

    sorted_users = sorted(users, key=total, reverse=True)[:limit]
    medals = ["🥇", "🥈", "🥉"]
    lines  = [f"🏆  TOP {limit} BY TRAFFIC", "─" * 24]
    for i, u in enumerate(sorted_users, 1):
        name = u.get("userId", u.get("username", "?"))
        gb   = round(total(u) / 1024 ** 3, 2)
        em   = "🟢" if u.get("enabled", True) else "🔴"
        rank = medals[i - 1] if i <= 3 else f"{i}."
        lines.append(f"  {rank} {em} {name} — {gb} GB")
    return "\n".join(lines)


def get_nodes_for_chart() -> list[dict]:
    return api_get_nodes()


def active_users_traffic(minutes: int = 10) -> str:
    from datetime import datetime, timezone, timedelta
    users  = api_get_users()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    active = []

    for u in users:
        last = u.get("traffic", {}).get("lastUpdate")
        if not last:
            continue
        try:
            ts = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if ts >= cutoff:
                name = u.get("userId", u.get("username", "?"))
                t    = u.get("traffic", {})
                rx   = round(t.get("rx", 0) / 1024 ** 3, 2)
                tx   = round(t.get("tx", 0) / 1024 ** 3, 2)
                active.append((name, rx, tx, ts))
        except Exception:
            continue

    if not active:
        return f"👥 Активных пользователей за последние {minutes} мин: 0"

    active.sort(key=lambda x: x[1] + x[2], reverse=True)
    lines = [f"👥 АКТИВНЫЕ ПОЛЬЗОВАТЕЛИ (последние {minutes} мин)\n" + "─" * 30]
    for name, rx, tx, ts in active:
        last_str = ts.strftime("%H:%M UTC")
        lines.append(f"🟢 {name}\n   ⬇ {rx} GB  ⬆ {tx} GB  🕐 {last_str}")

    lines.append("─" * 30)
    lines.append(f"Всего активных: {len(active)}")
    return "\n".join(lines)
