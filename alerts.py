"""
Real-time alert system:
  - 5-sec port-probe heartbeat with 2/3 false-positive filter
  - 60-sec API check (traffic spikes, node offline)
  - Integrates scheduler for expiry/daily alerts

Убрано: SSH auto-restart (API не поддерживает)
Добавлено: reset-status через API при падении ноды
"""

import asyncio
import time

from prober import probe_all, check_2_of_3, alerted_down
from nodes import get_nodes
from mcp import api_get_nodes_async, api_post
from events import log_event

alert_log: list[str] = []
muted_until: float = 0.0

HEARTBEAT_INTERVAL = 5
API_CHECK_INTERVAL = 60
TRAFFIC_SPIKE_GB   = 3

last_traffic: dict[str, int] = {}


def is_muted() -> bool:
    return time.time() < muted_until


def mute_alerts(hours: float):
    global muted_until
    muted_until = time.time() + hours * 3600


def unmute_alerts():
    global muted_until
    muted_until = 0.0


def get_alert_status() -> str:
    ts = time.strftime("%H:%M:%S")
    if is_muted():
        mins   = int((muted_until - time.time()) / 60)
        status = f"🔇 Алерты выключены — осталось {mins} мин\n"
    else:
        status = "🔔 Алерты АКТИВНЫ\n"

    status += f"🕐 Обновлено: {ts}\n"

    if alert_log:
        status += "\n📋 Последние алерты:\n"
        for entry in alert_log[-10:]:
            status += f"  {entry}\n"
    else:
        status += "\n✅ Алертов нет — всё в порядке"
    return status


def _log(msg: str):
    ts    = time.strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    alert_log.append(entry)
    if len(alert_log) > 200:
        alert_log.pop(0)


async def _send(app, admin_id: int, text: str):
    if is_muted():
        return
    _log(text.split("\n")[0])
    try:
        await app.bot.send_message(admin_id, text)
    except Exception as e:
        print(f"[ALERT] send error: {e}")


# ── Probe loop — every 5 sec ───────────────────────────────────────────────────

async def _probe_loop(app, admin_id: int):
    while True:
        try:
            nodes   = get_nodes()
            results = await probe_all(nodes)

            for r in results:
                node_id = r["node_id"]
                name    = r["name"]
                ok      = r["ok"]
                lat     = r.get("latency")

                confirmed_down = check_2_of_3(node_id, ok)

                if not ok and confirmed_down and node_id not in alerted_down:
                    alerted_down.add(node_id)
                    lat_str = f"{lat}ms" if lat else "no response"
                    await _send(
                        app, admin_id,
                        f"🔴 NODE DOWN: {name}\n"
                        f"   Port {r.get('port', 443)} — {lat_str}\n"
                        f"   Панель уведомлена, проверь статус в /ops",
                    )
                    log_event("node_down", name, lat_str)
                    # Сброс статуса через API панели
                    api_post(f"/api/nodes/{node_id}/reset-status")

                elif ok and node_id in alerted_down:
                    alerted_down.discard(node_id)
                    await _send(
                        app, admin_id,
                        f"🟢 RECOVERED: {name}\n"
                        f"   Latency: {lat}ms",
                    )
                    log_event("node_up", name, f"{lat}ms")

        except Exception as e:
            print(f"[PROBE LOOP] error: {e}")

        await asyncio.sleep(HEARTBEAT_INTERVAL)


# ── API loop — every 60 sec ────────────────────────────────────────────────────

async def _api_loop(app, admin_id: int):
    global last_traffic

    while True:
        await asyncio.sleep(API_CHECK_INTERVAL)
        try:
            node_list = await api_get_nodes_async()
            if isinstance(node_list, dict) and "error" in node_list:
                await _send(
                    app, admin_id,
                    f"⚠️ API FAIL: не удалось получить ноды\n{node_list['error']}",
                )
                continue

            for node in node_list:
                name     = node.get("name", "?")
                t        = node.get("traffic", {})
                rx_now   = t.get("rx", 0)
                rx_prev  = last_traffic.get(name, rx_now)
                delta_gb = (rx_now - rx_prev) / 1024 ** 3

                if delta_gb > TRAFFIC_SPIKE_GB:
                    await _send(
                        app, admin_id,
                        f"🚨 TRAFFIC SPIKE: {name}\n"
                        f"   +{round(delta_gb, 2)} GB за {API_CHECK_INTERVAL}s",
                    )
                    log_event("spike", name, f"+{round(delta_gb, 2)} GB")

                last_traffic[name] = rx_now

                online = node.get("onlineUsers", 0)
                if online > 50:
                    await _send(
                        app, admin_id,
                        f"⚡ ПЕРЕГРУЗКА: {name}\n   {online} клиентов подключено",
                    )

        except Exception as e:
            print(f"[API LOOP] error: {e}")


# ── Entry point ────────────────────────────────────────────────────────────────

async def monitor(app, admin_id: int):
    from scheduler import scheduler_loop
    await asyncio.gather(
        _probe_loop(app, admin_id),
        _api_loop(app, admin_id),
        scheduler_loop(app, admin_id),
    )
