"""
Модуль мониторинга белых списков РФ.

Логика:
1. Раз в день скачивает whitelist.txt с GitHub (908 доменов)
2. Раз в час проверяет топ-50 доменов на доступность как SNI через TLS
3. Сравнивает с текущим SNI нод из CELERITY API
4. Если текущий SNI недоступен — уведомляет и предлагает замену
5. Кнопка "Сменить SNI" обновляет ноду через API панели
"""

import asyncio
import ssl
import socket
import time
import random
from datetime import datetime, timezone

import requests
from mcp import api_get_nodes, _put

# ── Настройки ──────────────────────────────────────────────────────────────────

WHITELIST_URL  = "https://raw.githubusercontent.com/hxehex/russia-mobile-internet-whitelist/main/whitelist.txt"
CHECK_INTERVAL = 3600      # проверка каждый час
UPDATE_INTERVAL = 86400    # обновление списка раз в день
SNI_CHECK_TOP  = 50        # сколько доменов проверять за раз
SNI_CHECK_TIMEOUT = 3      # таймаут TLS подключения в секундах
PORT = 443

# ── Состояние ──────────────────────────────────────────────────────────────────

_whitelist_domains: list[str] = []
_working_domains:  list[str] = []
_last_whitelist_update: float = 0.0
_last_check: float = 0.0


# ── Загрузка whitelist ─────────────────────────────────────────────────────────

def fetch_whitelist() -> list[str]:
    """Скачивает whitelist.txt с GitHub."""
    try:
        r = requests.get(WHITELIST_URL, timeout=15)
        r.raise_for_status()
        domains = [
            line.strip()
            for line in r.text.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return domains
    except Exception as e:
        print(f"[WHITELIST] fetch error: {e}")
        return []


def update_whitelist_if_needed():
    global _whitelist_domains, _last_whitelist_update
    if time.time() - _last_whitelist_update > UPDATE_INTERVAL or not _whitelist_domains:
        domains = fetch_whitelist()
        if domains:
            _whitelist_domains = domains
            _last_whitelist_update = time.time()
            print(f"[WHITELIST] Updated: {len(_whitelist_domains)} domains")


# ── Проверка SNI ───────────────────────────────────────────────────────────────

def check_sni(domain: str, timeout: int = SNI_CHECK_TIMEOUT) -> bool:
    """
    Проверяет доступность домена как SNI через TLS подключение.
    Пытается установить TLS соединение — если удалось, домен доступен.
    """
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((domain, PORT), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                ssock.do_handshake()
                return True
    except Exception:
        return False


def check_domains_batch(domains: list[str]) -> list[str]:
    """Проверяет список доменов и возвращает только рабочие."""
    working = []
    for domain in domains:
        if check_sni(domain):
            working.append(domain)
    return working


async def check_domains_async(domains: list[str]) -> list[str]:
    """Асинхронная проверка доменов через executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_domains_batch, domains)


# ── Получение текущих SNI нод ──────────────────────────────────────────────────

def get_nodes_sni() -> dict[str, str]:
    """Возвращает словарь {node_id: sni} для всех VLESS нод."""
    nodes = api_get_nodes()
    result = {}
    for node in nodes:
        if node.get("type") == "xray":
            node_id = node["_id"]
            name    = node.get("name", "?")
            sni_list = node.get("xray", {}).get("realitySni", [])
            sni = sni_list[0] if sni_list else ""
            if sni:
                result[node_id] = {"name": name, "sni": sni}
    return result


# ── Смена SNI через API ────────────────────────────────────────────────────────

def update_node_sni(node_id: str, new_sni: str, new_dest: str = "") -> dict:
    """Обновляет SNI ноды через CELERITY API."""
    payload = {
        "xray": {
            "realitySni": [new_sni],
            "realityDest": new_dest or f"{new_sni}:443",
        }
    }
    return _put(f"/api/nodes/{node_id}", payload)


# ── Основной мониторинг ────────────────────────────────────────────────────────

async def check_whitelist_status() -> dict:
    """
    Проверяет статус белого списка и текущих SNI нод.
    Возвращает результат для отображения в боте.
    """
    global _working_domains, _last_check

    update_whitelist_if_needed()

    if not _whitelist_domains:
        return {
            "ok": False,
            "error": "Не удалось загрузить whitelist.txt",
            "working": [],
            "nodes_sni": {},
        }

    # Берём случайные 50 доменов для проверки
    sample = random.sample(_whitelist_domains, min(SNI_CHECK_TOP, len(_whitelist_domains)))
    working = await check_domains_async(sample)
    _working_domains = working
    _last_check = time.time()

    # Проверяем текущие SNI нод
    nodes_sni = get_nodes_sni()
    problem_nodes = {}

    for node_id, info in nodes_sni.items():
        current_sni = info["sni"]
        if not check_sni(current_sni):
            problem_nodes[node_id] = info

    return {
        "ok": True,
        "total_checked": len(sample),
        "working_count": len(working),
        "working_sample": working[:10],
        "nodes_sni": nodes_sni,
        "problem_nodes": problem_nodes,
        "last_check": datetime.now(timezone.utc).strftime("%H:%M UTC"),
        "whitelist_size": len(_whitelist_domains),
    }


def format_whitelist_status(result: dict) -> str:
    """Форматирует результат проверки для Telegram."""
    if not result.get("ok"):
        return f"❌ Ошибка: {result.get('error', 'неизвестно')}"

    lines = [
        "🌐  WHITELIST MONITOR",
        "─" * 28,
        f"📋  Доменов в списке:  {result['whitelist_size']}",
        f"🔍  Проверено:         {result['total_checked']}",
        f"✅  Доступных:         {result['working_count']}",
        f"🕐  Проверка:          {result['last_check']}",
        "",
    ]

    # Статус текущих SNI нод
    if result["nodes_sni"]:
        lines.append("📡  Текущие SNI нод:")
        for node_id, info in result["nodes_sni"].items():
            sni     = info["sni"]
            name    = info["name"]
            working = check_sni(sni)
            em      = "✅" if working else "❌"
            lines.append(f"  {em} {name}: {sni}")
        lines.append("")

    # Проблемные ноды
    if result.get("problem_nodes"):
        lines.append("⚠️  ТРЕБУЮТ ЗАМЕНЫ SNI:")
        for node_id, info in result["problem_nodes"].items():
            lines.append(f"  🔴 {info['name']}: {info['sni']} недоступен")
        lines.append("")
        lines.append("👆 Нажми кнопку ниже чтобы заменить SNI")
    else:
        lines.append("✅  Все SNI нод доступны")

    # Топ рабочих доменов
    if result.get("working_sample"):
        lines.append("")
        lines.append("🔝  Рабочие домены (топ из проверенных):")
        for d in result["working_sample"][:5]:
            lines.append(f"  • {d}")

    return "\n".join(lines)


def get_replacement_sni() -> str:
    """Возвращает случайный рабочий SNI из последней проверки."""
    if _working_domains:
        return random.choice(_working_domains)
    # Если нет кэша — проверяем несколько популярных доменов
    fallback = ["avito.ru", "ozon.ru", "vk.com", "ya.ru", "yandex.ru", "2gis.ru"]
    for domain in fallback:
        if check_sni(domain):
            return domain
    return ""


# ── Фоновый цикл ──────────────────────────────────────────────────────────────

async def whitelist_monitor_loop(app, admin_id: int):
    """Фоновый цикл мониторинга белого списка."""
    # Первый запуск через 5 минут после старта
    await asyncio.sleep(300)

    while True:
        try:
            result = await check_whitelist_status()

            # Уведомляем только если есть проблемные ноды
            if result.get("problem_nodes"):
                msg = format_whitelist_status(result)
                await app.bot.send_message(admin_id, msg)

        except Exception as e:
            print(f"[WHITELIST MONITOR] error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)
