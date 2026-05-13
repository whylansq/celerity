"""
Scheduled background tasks:
  - Daily summary report (every 24 h)
  - User expiry warnings   (every 6 h)
  - User traffic warnings  (every 6 h)
  - Server resource alerts (every 5 min via SSH)
"""

import asyncio
import json
import time
from datetime import datetime, timezone

from mcp import mcp
from nodes import get_stats
from server import get_unique_server_nodes, get_disk_usage_pct, get_cpu_pct

# ── Tunables ───────────────────────────────────────────────────────────────────
daily_report_enabled: bool  = True
last_daily_report:    float = 0.0
last_user_check:      float = 0.0
last_resource_check:  float = 0.0

DAILY_INTERVAL    = 86400   # 24 h
USER_CHECK_INTERVAL = 21600 # 6 h
RESOURCE_INTERVAL = 300     # 5 min

DISK_ALERT_PCT  = 85.0
CPU_ALERT_PCT   = 90.0
EXPIRY_WARN_DAYS = 3
TRAFFIC_WARN_PCT = 80.0

_resource_alerted: set[str] = set()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_users() -> list[dict]:
    data = mcp("query", {"resource": "users"})
    try:
        return json.loads(data["result"]["content"][0]["text"])["users"]
    except Exception:
        return []


# ── Report builders ────────────────────────────────────────────────────────────

def build_daily_report() -> str:
    stats = get_stats()
    u = stats.get("users", {})
    n = stats.get("nodes", {})
    node_list = n.get("list", [])

    total_rx = sum(nd.get("traffic", {}).get("rx", 0) for nd in node_list)
    total_tx = sum(nd.get("traffic", {}).get("tx", 0) for nd in node_list)
    rx_gb = round(total_rx / 1024 ** 3, 2)
    tx_gb = round(total_tx / 1024 ** 3, 2)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"📅  DAILY REPORT",
        f"🕐  {ts}",
        "─" * 30,
        f"📡  Ноды:    {n.get('online', 0)}/{n.get('total', 0)} онлайн",
        f"👤  Юзеры:   {u.get('enabled', 0)} активных / {u.get('total', 0)} всего",
        f"👥  Онлайн:  {stats.get('onlineUsers', 0)} клиентов",
        "",
        "📊  Трафик по нодам:",
    ]
    for nd in node_list:
        name    = nd.get("name", "?")
        em      = "🟢" if nd.get("status") == "online" else "🔴"
        rx      = round(nd.get("traffic", {}).get("rx", 0) / 1024 ** 3, 2)
        tx      = round(nd.get("traffic", {}).get("tx", 0) / 1024 ** 3, 2)
        clients = nd.get("online", 0)
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
    for u in _get_users():
        exp_str = u.get("expireAt")
        if not exp_str or not u.get("enabled", True):
            continue
        try:
            exp       = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            days_left = (exp - now).days
            if 0 <= days_left <= EXPIRY_WARN_DAYS:
                alerts.append(
                    f"⏰  ИСТЕКАЕТ: {u['username']}\n"
                    f"   Осталось {days_left} дн. — {exp_str[:10]}"
                )
        except Exception:
            pass
    return alerts


def check_traffic_limit_warnings() -> list[str]:
    alerts = []
    for u in _get_users():
        limit = u.get("trafficLimit", 0)
        if not limit or not u.get("enabled", True):
            continue
        t    = u.get("traffic", {})
        used = t.get("rx", 0) + t.get("tx", 0)
        pct  = used / limit * 100
        if pct >= TRAFFIC_WARN_PCT:
            alerts.append(
                f"📦  ЛИМИТ: {u['username']}\n"
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


# ── Main loop ──────────────────────────────────────────────────────────────────

async def scheduler_loop(app, admin_id: int):
    global last_daily_report, last_user_check, last_resource_check

    while True:
        await asyncio.sleep(60)
        now = time.time()

        # ── Daily report ───────────────────────────────────────────────────────
        if daily_report_enabled and (now - last_daily_report) >= DAILY_INTERVAL:
            last_daily_report = now
            try:
                await app.bot.send_message(admin_id, build_daily_report())
            except Exception as e:
                print(f"[SCHEDULER] daily report: {e}")

        # ── User checks (every 6 h) ────────────────────────────────────────────
        if (now - last_user_check) >= USER_CHECK_INTERVAL:
            last_user_check = now
            try:
                for msg in check_expiry_warnings():
                    await app.bot.send_message(admin_id, msg)
                for msg in check_traffic_limit_warnings():
                    await app.bot.send_message(admin_id, msg)
            except Exception as e:
                print(f"[SCHEDULER] user check: {e}")

        # ── Resource checks (every 5 min) ──────────────────────────────────────
        if (now - last_resource_check) >= RESOURCE_INTERVAL:
            last_resource_check = now
            try:
                for msg in check_server_resources():
                    await app.bot.send_message(admin_id, msg)
            except Exception as e:
                print(f"[SCHEDULER] resource check: {e}")
