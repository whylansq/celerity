import asyncio
import time
from collections import defaultdict, deque

# Last 3 probe results per node — for 2/3 filter
probe_history = defaultdict(lambda: deque(maxlen=3))
# Latency history for charts: node_id -> [(timestamp, ms), ...]
latency_history = defaultdict(list)
MAX_LATENCY_POINTS = 60

# Current probe state: node_id -> result dict
probe_results = {}

# Track whether we already alerted for this outage (reset on recovery)
alerted_down = set()


async def probe_tcp(host, port, timeout=3.0):
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
        except Exception:
            pass
        latency = round((time.monotonic() - start) * 1000, 1)
        return True, latency
    except Exception:
        return False, None


async def probe_node(node):
    node_id = node["_id"]
    name = node.get("name", "?")
    ip = node.get("ip", "")
    ntype = node.get("type", "hysteria")
    port = int(node.get("port", 443))

    if not ip:
        return {"node_id": node_id, "name": name, "ok": False, "latency": None, "type": ntype}

    ok, latency = await probe_tcp(ip, port)

    if latency is not None:
        latency_history[node_id].append((time.time(), latency))
        if len(latency_history[node_id]) > MAX_LATENCY_POINTS:
            latency_history[node_id].pop(0)

    result = {
        "node_id": node_id,
        "name": name,
        "type": ntype,
        "ip": ip,
        "port": port,
        "ok": ok,
        "latency": latency,
        "timestamp": time.time(),
    }
    probe_results[node_id] = result
    return result


async def probe_all(nodes):
    tasks = [probe_node(n) for n in nodes]
    return await asyncio.gather(*tasks)


def check_2_of_3(node_id, current_ok):
    """Add result and return True if 2 or more of last 3 checks failed."""
    probe_history[node_id].append(current_ok)
    failures = sum(1 for r in probe_history[node_id] if not r)
    return failures >= 2


def get_probe_summary():
    if not probe_results:
        return "⏳ No probe data yet — monitoring starting..."

    text = "🔍 REAL-TIME PORT PROBE\n\n"
    for node_id, r in probe_results.items():
        emoji = "🟢" if r["ok"] else "🔴"
        lat = f"{r['latency']}ms" if r["latency"] else "timeout"
        ntype = "HYS" if r.get("type") == "hysteria" else "VLS"
        text += f"{emoji} {r['name']} [{ntype}:{r.get('port',443)}] — {lat}\n"

    ts = time.strftime("%H:%M:%S")
    text += f"\n🕐 Last probe: {ts}"
    return text


def get_geo_comparison():
    fi_results = []
    ge_results = []

    for node_id, r in probe_results.items():
        name = r.get("name", "").upper()
        ok = r.get("ok", False)
        lat = r.get("latency")
        entry = {"name": r["name"], "ok": ok, "latency": lat}

        if "FI" in name:
            fi_results.append(entry)
        elif "GE" in name or "DE" in name:
            ge_results.append(entry)

    text = "🧭 GEO LATENCY COMPARISON\n\n"

    def fmt_group(results, flag, label):
        if not results:
            return f"{flag} {label}: no data\n\n"
        lats = [r["latency"] for r in results if r["latency"] is not None]
        avg = round(sum(lats) / len(lats), 1) if lats else None
        out = f"{flag} {label}"
        if avg:
            out += f" — avg {avg}ms\n"
        else:
            out += " — timeout\n"
        for r in results:
            em = "🟢" if r["ok"] else "🔴"
            lat_str = f"{r['latency']}ms" if r["latency"] else "❌"
            out += f"   {em} {r['name']}: {lat_str}\n"
        return out + "\n"

    fi_str = fmt_group(fi_results, "🇫🇮", "Finland")
    ge_str = fmt_group(ge_results, "🇩🇪", "Germany")
    text += fi_str + ge_str

    fi_lats = [r["latency"] for r in fi_results if r["latency"]]
    ge_lats = [r["latency"] for r in ge_results if r["latency"]]
    if fi_lats and ge_lats:
        avg_fi = sum(fi_lats) / len(fi_lats)
        avg_ge = sum(ge_lats) / len(ge_lats)
        better = "🇫🇮 Finland" if avg_fi < avg_ge else "🇩🇪 Germany"
        diff = round(abs(avg_fi - avg_ge), 1)
        text += f"🏆 Better: {better} (by {diff}ms)"

    return text.strip()
