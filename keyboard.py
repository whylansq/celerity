from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

# ── Main reply keyboard ────────────────────────────────────────────────────────
# Убраны: "📡 Статус" (дубль OPS), "⚡ Действия" (перенесено в Настройки)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["➕ Добавить юзера", "📅 Отчёт"],
        ["🧠 OPS", "👥 Юзеры", "📊 Аналитика"],
        ["🔔 Алерты", "⚙️ Настройки"],
    ],
    resize_keyboard=True,
)


# ── OPS ────────────────────────────────────────────────────────────────────────

def ops_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Обновить",     callback_data="ops_refresh"),
            InlineKeyboardButton("🔍 Порт-проб",    callback_data="ops_probe"),
            InlineKeyboardButton("🧭 Гео",          callback_data="ops_geo"),
        ],
        [
            InlineKeyboardButton("🖥 Серверы",      callback_data="ops_server"),
            InlineKeyboardButton("💻 SSH",           callback_data="ops_ssh_menu"),
            InlineKeyboardButton("♻️ Ребут",         callback_data="ops_reboot_menu"),
        ],
        [
            InlineKeyboardButton("🚨 Auto-Heal",    callback_data="ops_heal"),
            InlineKeyboardButton("💀 Panic",         callback_data="ops_panic"),
        ],
    ])


# ── Users ──────────────────────────────────────────────────────────────────────

def users_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список",           callback_data="users_list")],
        [
            InlineKeyboardButton("➕ Создать",        callback_data="users_create"),
            InlineKeyboardButton("🗑 Удалить",        callback_data="users_delete"),
        ],
        [
            InlineKeyboardButton("✅ Включить",       callback_data="users_enable"),
            InlineKeyboardButton("🚫 Отключить",      callback_data="users_disable"),
            InlineKeyboardButton("ℹ️ Инфо",           callback_data="users_info"),
        ],
        [
            InlineKeyboardButton("🔄 Сброс трафика",  callback_data="users_reset_traffic"),
            InlineKeyboardButton("📦 Лимит",          callback_data="users_set_limit"),
        ],
        [
            InlineKeyboardButton("📅 Продлить",       callback_data="users_extend_expiry"),
            InlineKeyboardButton("📱 Девайсы",        callback_data="users_set_devices"),
        ],
        [
            InlineKeyboardButton("🔗 Подписка",       callback_data="users_sub"),
            InlineKeyboardButton("📷 QR-код",         callback_data="users_qr"),
        ],
    ])


# ── Analytics ──────────────────────────────────────────────────────────────────

def analytics_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 Обзор",          callback_data="analytics_traffic"),
            InlineKeyboardButton("👥 Онлайн",         callback_data="analytics_online"),
            InlineKeyboardButton("🏆 Топ",            callback_data="analytics_top"),
        ],
        [
            InlineKeyboardButton("🇫🇮 FI",            callback_data="analytics_fi"),
            InlineKeyboardButton("🇩🇪 GE",            callback_data="analytics_de"),
        ],
        [
            InlineKeyboardButton("📊 График трафика",    callback_data="analytics_chart_traffic"),
            InlineKeyboardButton("📉 График латентн.",   callback_data="analytics_chart_latency"),
        ],
    ])


# ── Settings (Настройки + бывшие Действия) ────────────────────────────────────

def settings_keyboard(daily_on: bool = True):
    label = "📅 Daily: ✅" if daily_on else "📅 Daily: ❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Найти ноды в панели", callback_data="settings_discover")],
        [
            InlineKeyboardButton("🔄 Рестарт всех",     callback_data="action_restart_all"),
            InlineKeyboardButton("💀 Panic restart",     callback_data="ops_panic"),
        ],
        [
            InlineKeyboardButton("⚡ Только Hysteria",   callback_data="action_restart_hys"),
            InlineKeyboardButton("🌐 Только VLESS",      callback_data="action_restart_vless"),
        ],
        [
            InlineKeyboardButton("🔁 Синхронизация",     callback_data="action_sync"),
            InlineKeyboardButton("💾 Бэкап",             callback_data="action_backup"),
        ],
        [
            InlineKeyboardButton("🔧 Переустановить",    callback_data="action_reinstall_menu"),
            InlineKeyboardButton(label,                   callback_data="alerts_toggle_daily"),
        ],
    ])


def settings_node_restart_keyboard(nodes: list[dict]) -> InlineKeyboardMarkup:
    """Динамические кнопки рестарта нод из API."""
    rows = []
    row  = []
    for node in nodes:
        name    = node.get("name", "?")
        flag    = node.get("flag", "📡")
        node_id = node["_id"]
        btn     = InlineKeyboardButton(
            f"{flag} {name}",
            callback_data=f"action_restart_node_{node_id}",
        )
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


# ── Alerts ─────────────────────────────────────────────────────────────────────

def alerts_keyboard_with_state(daily_on: bool):
    label = "📅 Daily ✅" if daily_on else "📅 Daily ❌"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Лог алертов",   callback_data="alerts_status"),
            InlineKeyboardButton("📅 Отчёт сейчас",  callback_data="alerts_report_now"),
        ],
        [
            InlineKeyboardButton("🔇 1ч",  callback_data="alerts_mute_1"),
            InlineKeyboardButton("🔇 3ч",  callback_data="alerts_mute_3"),
            InlineKeyboardButton("🔇 6ч",  callback_data="alerts_mute_6"),
        ],
        [
            InlineKeyboardButton("🔔 Включить",  callback_data="alerts_unmute"),
            InlineKeyboardButton(label,           callback_data="alerts_toggle_daily"),
        ],
    ])


# ── Node pickers ───────────────────────────────────────────────────────────────

def node_picker_keyboard(action_prefix: str, nodes: list[tuple]) -> InlineKeyboardMarkup:
    buttons = []
    for node_id, name, ntype in nodes:
        tag = "⚡ HYS" if ntype == "hysteria" else "🌐 VLS"
        buttons.append([InlineKeyboardButton(
            f"📡 {name}  [{tag}]",
            callback_data=f"{action_prefix}_{node_id}_{ntype}",
        )])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def reinstall_keyboard(nodes: list[tuple]) -> InlineKeyboardMarkup:
    buttons = []
    for node_id, name, ntype in nodes:
        tag = "⚡ HYS" if ntype == "hysteria" else "🌐 VLS"
        buttons.append([InlineKeyboardButton(
            f"🔧 {name}  [{tag}]",
            callback_data=f"reinstall_{node_id}_{ntype}",
        )])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


# ── Generic ────────────────────────────────────────────────────────────────────

def confirm_keyboard(action: str, target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{action}_{target}"),
        InlineKeyboardButton("❌ Отмена",       callback_data="cancel"),
    ]])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️ Назад", callback_data="back_main"),
    ]])
