"""
REST API клиент для CELERITY-panel.
Заменяет старый MCP-протокол на прямые HTTP-вызовы к /api/*.

Переменные окружения:
  PANEL_URL  — базовый URL панели, напр. https://panel.example.com
  API_KEY    — Bearer-токен для авторизации
"""

import json
import os
import time

import aiohttp
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY   = os.getenv("API_KEY", "")
PANEL_URL = os.getenv("PANEL_URL", os.getenv("MCP_URL", "")).rstrip("/")

# Убираем /api/mcp если случайно указан старый URL
if PANEL_URL.endswith("/api/mcp"):
    PANEL_URL = PANEL_URL[: -len("/api/mcp")]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


# ── In-memory cache ────────────────────────────────────────────────────────────

_CACHE: dict[str, dict] = {}

_CACHE_TTL: dict[str, int] = {
    "nodes": 10,
    "users": 10,
}


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["value"]
    return None


def _cache_set(key: str, value, ttl: int):
    _CACHE[key] = {"value": value, "expires": time.time() + ttl}


def cache_invalidate(resource: str | None = None):
    if resource:
        _CACHE.pop(resource, None)
    else:
        _CACHE.clear()


# ── Sync REST helpers ──────────────────────────────────────────────────────────

def _get(path: str, cache_key: str | None = None):
    if cache_key:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
    try:
        r = requests.get(f"{PANEL_URL}{path}", headers=_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        if cache_key:
            ttl = next((v for k, v in _CACHE_TTL.items() if k in cache_key), 10)
            _cache_set(cache_key, data, ttl)
        return data
    except requests.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _post(path: str, body: dict | None = None) -> dict:
    try:
        r = requests.post(f"{PANEL_URL}{path}", headers=_headers(), json=body or {}, timeout=30)
        r.raise_for_status()
        return r.json() if r.text.strip() else {"ok": True}
    except requests.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _put(path: str, body: dict) -> dict:
    try:
        r = requests.put(f"{PANEL_URL}{path}", headers=_headers(), json=body, timeout=30)
        r.raise_for_status()
        return r.json() if r.text.strip() else {"ok": True}
    except requests.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _delete(path: str) -> dict:
    try:
        r = requests.delete(f"{PANEL_URL}{path}", headers=_headers(), timeout=30)
        r.raise_for_status()
        return r.json() if r.text.strip() else {"ok": True}
    except requests.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


# ── Async REST helpers ─────────────────────────────────────────────────────────

async def _aget(path: str, cache_key: str | None = None):
    if cache_key:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{PANEL_URL}{path}", headers=_headers()) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                if cache_key:
                    ttl = next((v for k, v in _CACHE_TTL.items() if k in cache_key), 10)
                    _cache_set(cache_key, data, ttl)
                return data
    except aiohttp.ClientResponseError as e:
        return {"error": f"HTTP {e.status}: {e.message}"}
    except Exception as e:
        return {"error": str(e)}


async def _apost(path: str, body: dict | None = None) -> dict:
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{PANEL_URL}{path}", headers=_headers(), json=body or {}) as resp:
                resp.raise_for_status()
                text = await resp.text()
                return await resp.json(content_type=None) if text.strip() else {"ok": True}
    except aiohttp.ClientResponseError as e:
        return {"error": f"HTTP {e.status}: {e.message}"}
    except Exception as e:
        return {"error": str(e)}


# ── Public API — Users ─────────────────────────────────────────────────────────

def api_get_users() -> list[dict]:
    data = _get("/api/users", cache_key="users")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("users", [])
    return []


def api_create_user(payload: dict) -> dict:
    cache_invalidate("users")
    return _post("/api/users", payload)


def api_update_user(user_id: str, payload: dict) -> dict:
    cache_invalidate("users")
    return _put(f"/api/users/{user_id}", payload)


def api_delete_user(user_id: str) -> dict:
    cache_invalidate("users")
    return _delete(f"/api/users/{user_id}")


def api_enable_user(user_id: str) -> dict:
    cache_invalidate("users")
    return _post(f"/api/users/{user_id}/enable")


def api_disable_user(user_id: str) -> dict:
    cache_invalidate("users")
    return _post(f"/api/users/{user_id}/disable")


# ── Public API — Nodes ─────────────────────────────────────────────────────────

def api_get_nodes() -> list[dict]:
    data = _get("/api/nodes", cache_key="nodes")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("nodes", [])
    return []


def api_sync() -> dict:
    cache_invalidate()
    return _post("/api/sync")


# ── Public API — SSH ───────────────────────────────────────────────────────────

def api_ssh(node_id: str, command: str) -> tuple[str | None, str | None]:
    data = _post(f"/api/nodes/{node_id}/ssh", {"command": command})
    if "error" in data:
        return None, str(data["error"])
    output = data.get("output") or data.get("result") or data.get("stdout")
    if output is None:
        output = json.dumps(data)
    return str(output), None


async def api_ssh_async(node_id: str, command: str) -> tuple[str | None, str | None]:
    data = await _apost(f"/api/nodes/{node_id}/ssh", {"command": command})
    if "error" in data:
        return None, str(data["error"])
    output = data.get("output") or data.get("result") or data.get("stdout")
    if output is None:
        output = json.dumps(data)
    return str(output), None


async def api_get_nodes_async() -> list[dict]:
    data = await _aget("/api/nodes", cache_key="nodes")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("nodes", [])
    return []


# ── Backward-compat обёртки (используются в nodes.py, backup.py, server.py) ───

def mcp(tool: str, arguments: dict | None = None) -> dict:
    args = dict(arguments or {})

    if tool == "query":
        resource = args.get("resource", "")
        if resource == "users":
            return {"_users": api_get_users()}
        if resource in ("nodes", "stats"):
            return {"_nodes": api_get_nodes()}
        return {"error": f"unknown resource: {resource}"}

    if tool == "create_user":
        return api_create_user(args)

    if tool == "update_user":
        uid = args.pop("userId", None) or args.pop("_id", None)
        if not uid:
            return {"error": "userId required"}
        return api_update_user(uid, args)

    if tool == "delete_user":
        uid = args.get("userId") or args.get("_id")
        return api_delete_user(uid) if uid else {"error": "userId required"}

    if tool == "reset_user_traffic":
        uid = args.get("userId") or args.get("_id")
        return api_update_user(uid, {"traffic": {"rx": 0, "tx": 0}}) if uid else {"error": "userId required"}

    if tool == "execute_ssh":
        node_id = args.get("nodeId") or args.get("node_id")
        out, err = api_ssh(node_id, args.get("command", ""))
        return {"error": err} if err else {"_output": out}

    if tool == "sync":
        return api_sync()

    return {"error": f"unknown tool: {tool}"}


async def mcp_async(tool: str, arguments: dict | None = None) -> dict:
    args = dict(arguments or {})

    if tool == "query":
        resource = args.get("resource", "")
        if resource in ("nodes", "stats"):
            nodes = await api_get_nodes_async()
            return {"_nodes": nodes}
        if resource == "users":
            return {"_users": api_get_users()}
        return {"error": f"unknown resource: {resource}"}

    if tool == "execute_ssh":
        node_id = args.get("nodeId") or args.get("node_id")
        out, err = await api_ssh_async(node_id, args.get("command", ""))
        return {"error": err} if err else {"_output": out}

    return mcp(tool, arguments)


def api_post(path: str, body: dict | None = None) -> dict:
    """Public alias for _post — used by alerts.py and other modules."""
    return _post(path, body)
