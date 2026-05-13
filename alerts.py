"""
Real-time alert system:
  - 5-sec port-probe heartbeat with 2/3 false-positive filter
  - 60-sec API check (traffic spikes, overload, API health)
  - Integrates scheduler for resource/expiry/daily alerts
"""

import asyncio
import json
import time

from prober import probe_all, check_2_of_3, alerted_down
from nodes import get_nodes, restart_node
from mcp import mcp

# ── State ──────────────────────────────────────────────────────────────────────
alert_log: list[str] = []
muted_until: float = 0.0

HEARTBEAT_INTERVAL = 5
API_CHECK_INTERVAL = 60
TRAFFIC_SPIKE_GB = 3

last_traffic: dict[str, int] = {}


# ── Mute controls ──────────────────────────────────────────────────────────────

def is_muted() -> bool:
    return time.time() < muted_until


def mute_alerts(hours: float):
    global muted_until
    muted_until = time.time() + hours * 3600


def unmute_alerts():
    global muted_until
    muted_until = 0.0


def get_alert_status() -> str:
    if is_muted():
        mins = int((muted_until - time.time()) / 60)
        status = f"🔇 Alerts muted — {mins} min remaining\n"
    else:
        status = "🔔 Alerts ACTIVE\n"

    if alert_log:
        status += "\n📋 Recent alerts:\n"
        for entry in alert_log[-10:]:
            status += f"  {entry}\n"
    else:
        status += "\n✅ No recent alerts"
    return status


# ── Internal helpers ───────────────────────────────────────────────────────────

def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    alert_log.append(f"[{ts}] {msg}")
    if len(alert_log) > 200:
        alert_log.pop(0)


async def _send(app, admin_id: int, text: str, force: bool = False):
    """Send alert. Pass force=True to bypass mute (e.g. daily report)."""
    if not force and is_muted():
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
            nodes = get_nodes()
            results = await probe_all(nodes)

            for r in results:
                node_id = r["node_id"]
                name = r["name"]
                ok = r["ok"]
                lat = r.get("latency")

                confirmed_down = check_2_of_3(node_id, ok)

                if not ok and confirmed_down and node_id not in alerted_down:
                    alerted_down.add(node_id)
                    lat_str = f"{lat}ms" if lat else "no response"
                    await _send(
                        app, admin_id,
                        f"🔴 NODE DOWN: {name}\n"
                        f"   Port {r.get('port', 443)} — {lat_str}\n"
                        f"   ⚙️ Auto-restart triggered",
                    )
                    restart_node(node_id)

                elif ok and node_id in alerted_down:
                    alerted_down.discard(node_id)
                    await _send(
                        app, admin_id,
                        f"🟢 RECOVERED: {name}\n"
                        f"   Latency: {lat}ms",
                    )

        except Exception as e:
            print(f"[PROBE LOOP] error: {e}")

        await asyncio.sleep(HEARTBEAT_INTERVAL)


# ── API loop — every 60 sec ────────────────────────────────────────────────────

async def _api_loop(app, admin_id: int):
    global last_traffic

    while True:
        await asyncio.sleep(API_CHECK_INTERVAL)
        try:
            result = mcp("query", {"resource": "stats"})
            if "error" in result:
                await _send(
                    app, admin_id,
                    f"⚠️ API FAIL: MCP endpoint not responding\n{result['error']}",
                )
                continue

            raw = result["result"]["content"][0]["text"]
            stats = json.loads(raw)
            node_list = stats.get("nodes", {}).get("list", [])

            for node in node_list:
                name = node.get("name", "?")
                t = node.get("traffic", {})
                rx_now = t.get("rx", 0)
                rx_prev = last_traffic.get(name, rx_now)
                delta_gb = (rx_now - rx_prev) / 1024 ** 3

                if delta_gb > TRAFFIC_SPIKE_GB:
                    await _send(
                        app, admin_id,
                        f"🚨 TRAFFIC SPIKE: {name}\n"
                        f"   +{round(delta_gb, 2)} GB in {API_CHECK_INTERVAL}s",
                    )

                last_traffic[name] = rx_now

                # Overload alert
                online = node.get("online", 0)
                if online > 50:
                    await _send(
                        app, admin_id,
                        f"⚡ OVERLOAD: {name}\n   {online} clients connected",
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
