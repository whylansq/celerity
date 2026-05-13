import json
import os
from datetime import datetime, timezone, timedelta
from mcp import mcp
from configs import generate_qr


def _base_url() -> str:
    url = os.getenv("MCP_URL", "https://whitelist.soon.it/api/mcp")
    return url.replace("/api/mcp", "")


# ── Data access ────────────────────────────────────────────────────────────────

def get_users() -> list[dict]:
    data = mcp("query", {"resource": "users"})
    try:
        raw = data["result"]["content"][0]["text"]
        return json.loads(raw)["users"]
    except Exception:
        return []


def get_user_by_username(username: str) -> dict | None:
    for u in get_users():
        if u.get("username", "").lower() == username.lower():
            return u
    return None


# ── Formatters ─────────────────────────────────────────────────────────────────

def format_users() -> str:
    users = get_users()
    if not users:
        return "❌ No users found"

    lines = ["👥 USERS LIST\n"]
    for u in users:
        username = u.get("username", "unknown")
        enabled = u.get("enabled", True)
        t = u.get("traffic", {})
        rx = round(t.get("rx", 0) / 1024 ** 3, 2)
        tx = round(t.get("tx", 0) / 1024 ** 3, 2)
        expire = u.get("expireAt", "")[:10] if u.get("expireAt") else "∞"
        limit = u.get("trafficLimit", 0)

        em = "🟢" if enabled else "🔴"

        # Traffic bar if limit is set
        if limit:
            used = t.get("rx", 0) + t.get("tx", 0)
            pct = min(int(used / limit * 10), 10)
            bar = "█" * pct + "░" * (10 - pct)
            limit_str = f" [{bar}]"
        else:
            limit_str = ""

        lines.append(f"{em} {username} — ⬇️{rx}GB ⬆️{tx}GB{limit_str} | {expire}")

    lines.append(f"\nTotal: {len(users)}")
    return "\n".join(lines)


def get_user_info(username: str) -> str:
    u = get_user_by_username(username)
    if not u:
        return f"❌ User not found: {username}"

    enabled = u.get("enabled", True)
    t = u.get("traffic", {})
    rx = round(t.get("rx", 0) / 1024 ** 3, 2)
    tx = round(t.get("tx", 0) / 1024 ** 3, 2)
    total_gb = round((t.get("rx", 0) + t.get("tx", 0)) / 1024 ** 3, 2)

    limit = u.get("trafficLimit", 0)
    limit_str = f"{round(limit / 1024**3, 1)} GB" if limit else "∞"
    if limit:
        used = t.get("rx", 0) + t.get("tx", 0)
        pct = round(used / limit * 100, 1)
        limit_str += f" ({pct}% used)"

    expire = u.get("expireAt", "")[:10] if u.get("expireAt") else "Never"
    if u.get("expireAt"):
        try:
            exp = datetime.fromisoformat(u["expireAt"].replace("Z", "+00:00"))
            days_left = (exp - datetime.now(timezone.utc)).days
            expire += f" ({days_left}d left)"
        except Exception:
            pass

    devices = u.get("maxDevices", 0) or "∞"
    token = u.get("subscriptionToken", "")
    sub_url = f"{_base_url()}/sub/{token}" if token else "—"
    uid = u.get("userId", u.get("_id", "?"))

    em = "🟢 Active" if enabled else "🔴 Disabled"
    return (
        f"👤 {username}\n\n"
        f"Status: {em}\n"
        f"🆔 ID: {uid}\n"
        f"⬇️ RX: {rx} GB | ⬆️ TX: {tx} GB\n"
        f"📦 Total used: {total_gb} GB / {limit_str}\n"
        f"📅 Expires: {expire}\n"
        f"📱 Devices: {devices}\n"
        f"🔗 Sub: `{sub_url}`"
    )


# ── CRUD operations ────────────────────────────────────────────────────────────

def create_user(username: str, traffic_limit_gb: int = 0,
                expire_days: int = 0, max_devices: int = 0) -> tuple[bool, str]:
    payload: dict = {"username": username, "enabled": True}

    if traffic_limit_gb > 0:
        payload["trafficLimit"] = traffic_limit_gb * 1024 ** 3
    if expire_days > 0:
        exp = (datetime.now(timezone.utc) + timedelta(days=expire_days)).isoformat()
        payload["expireAt"] = exp
    if max_devices > 0:
        payload["maxDevices"] = max_devices

    data = mcp("create_user", payload)
    try:
        raw = data["result"]["content"][0]["text"]
        result = json.loads(raw)
        token = result.get("subscriptionToken", "")
        uid = result.get("userId", result.get("_id", "?"))
        sub_url = f"{_base_url()}/sub/{token}" if token else "—"

        extras = []
        if traffic_limit_gb:
            extras.append(f"📦 Limit: {traffic_limit_gb} GB")
        if expire_days:
            extras.append(f"📅 Expires: {expire_days} days")
        if max_devices:
            extras.append(f"📱 Devices: {max_devices}")

        extra_str = "\n" + "\n".join(extras) if extras else ""
        return True, (
            f"✅ User created!\n\n"
            f"👤 {username}\n"
            f"🆔 ID: {uid}"
            f"{extra_str}\n"
            f"🔗 Sub: `{sub_url}`"
        )
    except Exception as e:
        err = data.get("error", str(e))
        return False, f"❌ Failed to create user: {err}"


def delete_user(username: str) -> tuple[bool, str]:
    u = get_user_by_username(username)
    if not u:
        return False, f"❌ User not found: {username}"
    uid = u.get("_id") or u.get("userId")
    data = mcp("delete_user", {"userId": uid})
    try:
        return True, f"🗑 User deleted: {username}"
    except Exception as e:
        return False, f"❌ Delete failed: {e}"


def disable_user(username: str) -> tuple[bool, str]:
    u = get_user_by_username(username)
    if not u:
        return False, f"❌ User not found: {username}"
    uid = u.get("_id") or u.get("userId")
    mcp("update_user", {"userId": uid, "enabled": False})
    return True, f"🚫 User disabled: {username}"


def enable_user(username: str) -> tuple[bool, str]:
    u = get_user_by_username(username)
    if not u:
        return False, f"❌ User not found: {username}"
    uid = u.get("_id") or u.get("userId")
    mcp("update_user", {"userId": uid, "enabled": True})
    return True, f"✅ User enabled: {username}"


def reset_user_traffic(username: str) -> tuple[bool, str]:
    u = get_user_by_username(username)
    if not u:
        return False, f"❌ User not found: {username}"
    uid = u.get("_id") or u.get("userId")
    # Celerity reset traffic endpoint
    data = mcp("reset_user_traffic", {"userId": uid})
    # Fallback: try update_user with zeroed traffic
    if "error" in data:
        data = mcp("update_user", {"userId": uid, "traffic": {"rx": 0, "tx": 0}})
    return True, f"🔄 Traffic reset: {username}"


def set_traffic_limit(username: str, gb: float) -> tuple[bool, str]:
    u = get_user_by_username(username)
    if not u:
        return False, f"❌ User not found: {username}"
    uid = u.get("_id") or u.get("userId")
    limit_bytes = int(gb * 1024 ** 3) if gb > 0 else 0
    mcp("update_user", {"userId": uid, "trafficLimit": limit_bytes})
    lim_str = f"{gb} GB" if gb > 0 else "unlimited"
    return True, f"📦 Limit set to {lim_str}: {username}"


def extend_expiry(username: str, days: int) -> tuple[bool, str]:
    u = get_user_by_username(username)
    if not u:
        return False, f"❌ User not found: {username}"
    uid = u.get("_id") or u.get("userId")

    current_expire = u.get("expireAt")
    if current_expire:
        try:
            base = datetime.fromisoformat(current_expire.replace("Z", "+00:00"))
            # If already expired, extend from now
            if base < datetime.now(timezone.utc):
                base = datetime.now(timezone.utc)
        except Exception:
            base = datetime.now(timezone.utc)
    else:
        base = datetime.now(timezone.utc)

    new_expire = (base + timedelta(days=days)).isoformat()
    mcp("update_user", {"userId": uid, "expireAt": new_expire})
    return True, f"📅 Extended by {days} days: {username}\nNew expiry: {new_expire[:10]}"


def set_max_devices(username: str, count: int) -> tuple[bool, str]:
    u = get_user_by_username(username)
    if not u:
        return False, f"❌ User not found: {username}"
    uid = u.get("_id") or u.get("userId")
    mcp("update_user", {"userId": uid, "maxDevices": count})
    lim = str(count) if count > 0 else "unlimited"
    return True, f"📱 Device limit set to {lim}: {username}"


# ── Subscription helpers ───────────────────────────────────────────────────────

def get_user_subscription(username: str) -> str:
    u = get_user_by_username(username)
    if not u:
        return ""
    token = u.get("subscriptionToken", "")
    if token:
        return f"{_base_url()}/sub/{token}"
    return u.get("subscriptionUrl", u.get("subUrl", ""))


def get_user_qr(username: str) -> tuple[str | None, str]:
    sub_url = get_user_subscription(username)
    if not sub_url:
        return None, f"❌ No subscription found for: {username}"
    path = generate_qr(sub_url, f"qr_{username}.png")
    return path, sub_url
