from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["➕ Добавить юзера", "📅 Отчёт"],
        ["🧠 OPS", "👥 Юзеры", "📊 Аналитика"],
        ["🔔 Алерты", "⚙️ Настройки"],
    ],
    resize_keyboard=True,
)


def ops_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Обновить",   callback_data="ops_refresh"),
            InlineKeyboardButton("🔍 Порт-проб",  callback_data="ops_probe"),
            InlineKeyboardButton("🧭 Гео",        callback_data="ops_geo"),
        ],
        [
            InlineKeyboardButton("🖥 Серверы",    callback_data="ops_server"),
            InlineKeyboardButton("💀 Panic",       callback_data="ops_panic"),
        ],
    ])


def users_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список",            callback_data="users_list")],
        [
            InlineKeyboardButton("➕ Создать",          callback_data="users_create"),
            InlineKeyboardButton("🗑 Удалить",          callback_data="users_delete"),
        ],
        [
            InlineKeyboardButton("✅ Включить",         callback_data="users_enable"),
            InlineKeyboardButton("🚫 Отключить",        callback_data="users_disable"),
            InlineKeyboardButton("ℹ️ Инфо",             callback_data="users_info"),
        ],
        [
            InlineKeyboardButton("🔄 Сброс трафика",    callback_data="users_reset_traffic"),
            InlineKeyboardButton("📦 Лимит",            callback_data="users_set_limit"),
        ],
        [
            InlineKeyboardButton("📅 Продлить",         callback_data="users_extend_expiry"),
            InlineKeyboardButton("📱 Девайсы",          callback_data="users_set_devices"),
        ],
        [
            InlineKeyboardButton("🔗 Подписка",         callback_data="users_sub"),
            InlineKeyboardButton("📷 QR-код",           callback_data="users_qr"),
        ],
    ])


def analytics_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 Обзор",            callback_data="analytics_traffic"),
            InlineKeyboardButton("👥 Онлайн",           callback_data="analytics_online"),
            InlineKeyboardButton("🏆 Топ",              callback_data="analytics_top"),
        ],
        [
            InlineKeyboardButton("🟢 Активные (10м)",   callback_data="analytics_active"),
        ],
        [
            InlineKeyboardButton("🇫🇮 FI",              callback_data="analytics_fi"),
            InlineKeyboardButton("🇩🇪 GE",              callback_data="analytics_de"),
        ],
        [
            InlineKeyboardButton("📊 График трафика",   callback_data="analytics_chart_traffic"),
            InlineKeyboardButton("📉 Латентность",      callback_data="analytics_chart_latency"),
        ],
    ])


def settings_keyboard(daily_on: bool = True, reboot_on: bool = False):
    daily_label  = "📅 Daily: ✅" if daily_on  else "📅 Daily: ❌"
    reboot_label = "♻️ Авторестарт: ✅" if reboot_on else "♻️ Авторестарт: ❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Найти ноды в панели",  callback_data="settings_discover")],
        [
            InlineKeyboardButton("🔄 Рестарт всех нод",  callback_data="action_restart_all"),
            InlineKeyboardButton("💀 Panic restart",      callback_data="ops_panic"),
        ],
        [
            InlineKeyboardButton("⚡ Только Hysteria",    callback_data="action_restart_hys"),
            InlineKeyboardButton("🌐 Только VLESS",       callback_data="action_restart_vless"),
        ],
        [
            InlineKeyboardButton("🖥 Перезагрузить GE",  callback_data="reboot_server_GE"),
            InlineKeyboardButton("🖥 Перезагрузить FI",  callback_data="reboot_server_FI"),
        ],
        [
            InlineKeyboardButton("🔁 Синхронизация",      callback_data="action_sync"),
            InlineKeyboardButton("💾 Бэкап",              callback_data="action_backup"),
        ],
        [
            InlineKeyboardButton(daily_label,             callback_data="alerts_toggle_daily"),
            InlineKeyboardButton(reboot_label,            callback_data="toggle_auto_reboot"),
        ],
        [InlineKeyboardButton("🕐 Время авторестарта",   callback_data="set_reboot_time")],
    ])


def alerts_keyboard_with_state(daily_on: bool):
    label = "📅 Daily ✅" if daily_on else "📅 Daily ❌"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Лог алертов",  callback_data="alerts_status"),
            InlineKeyboardButton("📅 Отчёт сейчас", callback_data="alerts_report_now"),
        ],
        [
            InlineKeyboardButton("🔇 1ч", callback_data="alerts_mute_1"),
            InlineKeyboardButton("🔇 3ч", callback_data="alerts_mute_3"),
            InlineKeyboardButton("🔇 6ч", callback_data="alerts_mute_6"),
        ],
        [
            InlineKeyboardButton("🔔 Включить", callback_data="alerts_unmute"),
            InlineKeyboardButton(label,          callback_data="alerts_toggle_daily"),
        ],
    ])


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


def confirm_keyboard(action: str, target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{action}_{target}"),
        InlineKeyboardButton("❌ Отмена",       callback_data="cancel"),
    ]])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️ Назад", callback_data="back_main"),
    ]])
