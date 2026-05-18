import asyncio
import time
from datetime import datetime, timezone

from mcp import api_get_nodes, api_get_users
from server import get_unique_server_nodes, get_disk_usage_pct, get_cpu_pct

daily_report_enabled: bool = True
last_daily_report:    float = 0.0
last_user_check:      float = 0.0
last_resource_check:  float = 0.0

DAILY_INTERVAL      = 86400
USER_CHECK_INTERVAL = 21600
RESOURCE_INTERVAL   = 300

DISK_ALERT_PCT   = 85.0
CPU_ALERT_PCT    = 90.0
EXPIRY_WARN_DAYS = 3
TRAFFIC_WARN_PCT = 80.0

_resource_alerted: set[str] = set()


def build_daily_report() -> str:
    nodes    = api_get_nodes()
    users    = api_get_users()
    online   = sum(1 for n in nodes if n.get("status") == "online")
    active   = sum(1 for u in users if u.get("enabled", True))
    online_u = sum(n.get("onlineUsers", 0) for n in nodes)
    total_rx = sum(n.get("traffic", {}).get("rx", 0) for n in nodes)
    total_tx = sum(n.get("traffic", {}).get("tx", 0) for n in nodes)
    rx_gb    = round(total_rx / 1024 ** 3, 2)
    tx_gb    = round(total_tx / 1024 ** 3, 2)
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "📅  DAILY REPORT",
        f"🕐  {ts}",
        "─" * 30,
        f"📡  Ноды:    {online}/{len(nodes)} онлайн",
        f"👤  Юзеры:   {active} активных / {len(users)} всего",
        f"👥  Онлайн:  {online_u} клиентов",
        "",
        "📊  Трафик по нодам:",
    ]
    for n in nodes:
        name    = n.get("name", "?")
        em      = "🟢" if n.get("status") == "online" else "🔴"
        rx      = round(n.get("traffic", {}).get("rx", 0) / 1024 ** 3, 2)
        tx      = round(n.get("traffic", {}).get("tx", 0) / 1024 ** 3, 2)
        clients = n.get("onlineUsers", 0)
        lines.append(f"  {em} {name}: ⬇{rx}GB ⬆{tx}GB 👥{clients}")

    lines += [
        "─" * 30,
        f"⬇  Суммарная загрузка: {rx_gb} GB",
        f"⬆  Суммарная отдача:   {tx_gb} GB",
        f"📦  Итого:              {round(rx_gb + tx_gb, 2)} GB",
    ]
    return "\n".join(lines)


def check_expiry_warnings() -> list[str]:
    now    = datetime.now(timezone.utc)
    alerts = []
    for u in api_get_users():
        exp_str = u.get("expireAt")
        if not exp_str or not u.get("enabled", True):
            continue
        try:
            exp       = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            days_left = (exp - now).days
            name      = u.get("userId", u.get("username", "?"))
            if 0 <= days_left <= EXPIRY_WARN_DAYS:
                alerts.append(
                    f"⏰  ИСТЕКАЕТ: {name}\n"
                    f"   Осталось {days_left} дн. — {exp_str[:10]}"
                )
        except Exception:
            pass
    return alerts


def check_traffic_limit_warnings() -> list[str]:
    alerts = []
    for u in api_get_users():
        limit = u.get("trafficLimit", 0)
        if not limit or not u.get("enabled", True):
            continue
        t    = u.get("traffic", {})
        used = t.get("rx", 0) + t.get("tx", 0)
        pct  = used / limit * 100
        name = u.get("userId", u.get("username", "?"))
        if pct >= TRAFFIC_WARN_PCT:
            alerts.append(
                f"📦  ЛИМИТ: {name}\n"
                f"   {round(used/1024**3,2)}/{round(limit/1024**3,2)} GB ({pct:.0f}%)"
            )
    return alerts


def check_server_resources() -> list[str]:
    alerts = []
    for node in get_unique_server_nodes():
        nid = node["_id"]
        ip  = node.get("ip", nid)

        disk = get_disk_usage_pct(nid)
        if disk is not None:
            key = f"disk_{nid}"
            if disk >= DISK_ALERT_PCT:
                if key not in _resource_alerted:
                    _resource_alerted.add(key)
                    alerts.append(f"💿  ДИСК ЗАПОЛНЕН: {ip}\n   {disk:.1f}% использовано")
            else:
                _resource_alerted.discard(key)

        cpu = get_cpu_pct(nid)
        if cpu is not None:
            key = f"cpu_{nid}"
            if cpu >= CPU_ALERT_PCT:
                if key not in _resource_alerted:
                    _resource_alerted.add(key)
                    alerts.append(f"🔥  HIGH CPU: {ip}\n   {cpu:.1f}% нагрузка")
            else:
                _resource_alerted.discard(key)

    return alerts


async def scheduler_loop(app, admin_id: int):
    global last_daily_report, last_user_check, last_resource_check

    while True:
        await asyncio.sleep(60)
        now = time.time()

        if daily_report_enabled and (now - last_daily_report) >= DAILY_INTERVAL:
            last_daily_report = now
            try:
                await app.bot.send_message(admin_id, build_daily_report())
            except Exception as e:
                print(f"[SCHEDULER] daily report: {e}")

        if (now - last_user_check) >= USER_CHECK_INTERVAL:
            last_user_check = now
            try:
                for msg in check_expiry_warnings():
                    await app.bot.send_message(admin_id, msg)
                for msg in check_traffic_limit_warnings():
                    await app.bot.send_message(admin_id, msg)
            except Exception as e:
                print(f"[SCHEDULER] user check: {e}")

        if (now - last_resource_check) >= RESOURCE_INTERVAL:
            last_resource_check = now
            try:
                for msg in check_server_resources():
                    await app.bot.send_message(admin_id, msg)
            except Exception as e:
                print(f"[SCHEDULER] resource check: {e}")
