from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

# ── Bottom reply keyboard ──────────────────────────────────────────────────────

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📡 Статус", "➕ Добавить юзера", "📅 Отчёт"],
        ["🧠 OPS", "👥 Юзеры", "📊 Аналитика"],
        ["⚡ Действия", "🔔 Алерты", "⚙️ Настройки"],
    ],
    resize_keyboard=True,
)


# ── OPS ───────────────────────────────────────────────────────────────────────

def ops_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Статус нод",      callback_data="ops_status"),
         InlineKeyboardButton("🔄 Обновить",        callback_data="ops_refresh")],
        [InlineKeyboardButton("🖥 Серверы",         callback_data="ops_server"),
         InlineKeyboardButton("🔍 Порт-проб",       callback_data="ops_probe")],
        [InlineKeyboardButton("🧭 Гео-сравнение",   callback_data="ops_geo")],
        [InlineKeyboardButton("🚨 Auto-Heal",        callback_data="ops_heal"),
         InlineKeyboardButton("💀 Panic Restart",   callback_data="ops_panic")],
        [InlineKeyboardButton("💻 SSH-команда",     callback_data="ops_ssh_menu"),
         InlineKeyboardButton("♻️ Ребут сервера",   callback_data="ops_reboot_menu")],
    ])


# ── Users ──────────────────────────────────────────────────────────────────────

def users_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список",          callback_data="users_list")],
        [InlineKeyboardButton("➕ Создать",          callback_data="users_create"),
         InlineKeyboardButton("🗑 Удалить",         callback_data="users_delete")],
        [InlineKeyboardButton("🚫 Отключить",       callback_data="users_disable"),
         InlineKeyboardButton("✅ Включить",        callback_data="users_enable")],
        [InlineKeyboardButton("ℹ️ Инфо",            callback_data="users_info"),
         InlineKeyboardButton("🔄 Сброс трафика",   callback_data="users_reset_traffic")],
        [InlineKeyboardButton("📦 Установить лимит", callback_data="users_set_limit"),
         InlineKeyboardButton("📅 Продлить срок",   callback_data="users_extend_expiry")],
        [InlineKeyboardButton("📱 Устройства",      callback_data="users_set_devices"),
         InlineKeyboardButton("📷 QR-код",          callback_data="users_qr")],
        [InlineKeyboardButton("🔗 Подписка",        callback_data="users_sub")],
    ])


# ── Analytics ──────────────────────────────────────────────────────────────────

def analytics_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Общий обзор",      callback_data="analytics_traffic")],
        [InlineKeyboardButton("🇫🇮 Финляндия",       callback_data="analytics_fi"),
         InlineKeyboardButton("🇩🇪 Германия",        callback_data="analytics_de")],
        [InlineKeyboardButton("👥 Онлайн клиенты",   callback_data="analytics_online"),
         InlineKeyboardButton("🏆 Топ юзеров",       callback_data="analytics_top")],
        [InlineKeyboardButton("📊 График трафика",   callback_data="analytics_chart_traffic"),
         InlineKeyboardButton("📉 График латентности", callback_data="analytics_chart_latency")],
    ])


# ── Actions ────────────────────────────────────────────────────────────────────

def actions_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇫🇮 Restart FI",       callback_data="action_restart_fi"),
         InlineKeyboardButton("🇩🇪 Restart GE",       callback_data="action_restart_ge")],
        [InlineKeyboardButton("⚡ Только Hysteria",   callback_data="action_restart_hys"),
         InlineKeyboardButton("🌐 Только VLESS",      callback_data="action_restart_vless")],
        [InlineKeyboardButton("🔄 Перезапустить всё", callback_data="action_restart_all")],
        [InlineKeyboardButton("🔁 Синх. ноды",       callback_data="action_sync"),
         InlineKeyboardButton("💾 Бэкап конфигов",   callback_data="action_backup")],
        [InlineKeyboardButton("🔧 Переустановить",    callback_data="action_reinstall_menu")],
    ])


# ── Alerts ─────────────────────────────────────────────────────────────────────

def alerts_keyboard_with_state(daily_on: bool):
    label = "📅 Daily Report ✅" if daily_on else "📅 Daily Report ❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Лог алертов",     callback_data="alerts_status"),
         InlineKeyboardButton("📅 Отчёт сейчас",   callback_data="alerts_report_now")],
        [InlineKeyboardButton("🔇 Тихо 1ч",         callback_data="alerts_mute_1"),
         InlineKeyboardButton("🔇 Тихо 3ч",         callback_data="alerts_mute_3"),
         InlineKeyboardButton("🔇 Тихо 6ч",         callback_data="alerts_mute_6")],
        [InlineKeyboardButton("🔔 Включить",         callback_data="alerts_unmute")],
        [InlineKeyboardButton(label,                 callback_data="alerts_toggle_daily")],
    ])


# ── Node pickers ───────────────────────────────────────────────────────────────

def node_picker_keyboard(action_prefix: str, nodes: list[tuple]) -> InlineKeyboardMarkup:
    """nodes: [(node_id, name, type), …]"""
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{action}_{target}"),
         InlineKeyboardButton("❌ Отмена",       callback_data="cancel")],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ])
