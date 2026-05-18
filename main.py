import asyncio
import logging
import os
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.error import BadRequest, Conflict, NetworkError, TimedOut
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)

from keyboard import (
    MAIN_KEYBOARD, ops_keyboard, users_keyboard, analytics_keyboard,
    settings_keyboard, settings_node_restart_keyboard,
    alerts_keyboard_with_state, reinstall_keyboard, node_picker_keyboard,
    confirm_keyboard, back_keyboard,
)
from nodes import format_status, restart_by_name, restart_all_nodes, panic_restart, get_nodes_inline_list, get_nodes
from mcp import api_get_nodes, api_sync
from users import (
    format_users, create_user, delete_user, disable_user, enable_user,
    get_user_qr, get_user_subscription, get_user_info, reset_user_traffic,
    set_traffic_limit, extend_expiry, set_max_devices,
)
from traffic import (
    traffic_stats, node_stats_by_pattern, online_clients,
    top_users_by_traffic, get_nodes_for_chart,
)
from alerts import monitor, mute_alerts, unmute_alerts, get_alert_status
from prober import get_probe_summary, get_geo_comparison
from charts import latency_chart, traffic_chart
from backup import backup_all, reinstall_node, cleanup_backup
from server import format_server_stats, ssh_command, reboot_server
from scheduler import build_daily_report, check_expiry_warnings, check_traffic_limit_warnings
import scheduler as _sched
from configs import cleanup_qr

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID  = int(os.getenv("ADMIN_ID"))

(WAIT_CREATE, WAIT_DELETE, WAIT_DISABLE, WAIT_ENABLE, WAIT_INFO,
 WAIT_RESET_TRAFFIC, WAIT_SET_LIMIT, WAIT_EXTEND_EXPIRY, WAIT_SET_DEVICES,
 WAIT_SUB, WAIT_QR, WAIT_SSH_NODE, WAIT_SSH_CMD) = range(13)

_SECTION_BUTTONS = {
    "➕ Добавить юзера", "📅 Отчёт",
    "🧠 OPS", "👥 Юзеры", "📊 Аналитика",
    "🔔 Алерты", "⚙️ Настройки",
}


async def guard(update: Update) -> bool:
    if update.effective_user.id != ADMIN_ID:
        if update.message:
            await update.message.reply_text("⛔ Нет доступа")
        elif update.callback_query:
            await update.callback_query.answer("⛔ Нет доступа", show_alert=True)
        return False
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    context.user_data.clear()
    await update.message.reply_text(
        "🚀  *PERSONAL OPS PANEL*\n\nCelerity C3 · личный VPN\n\nИспользуй кнопки ниже 👇",
        parse_mode="Markdown", reply_markup=MAIN_KEYBOARD,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    await update.message.reply_text(
        "📖  *СПРАВКА ПО БОТУ*\n\n"
        "*Разделы:*\n"
        "  🧠 OPS — ноды, серверы, SSH, ребут\n"
        "  👥 Юзеры — полное управление\n"
        "  📊 Аналитика — трафик, топы, графики\n"
        "  🔔 Алерты — лог, отчёт, mute\n"
        "  ⚙️ Настройки — рестарты, синх, бэкап\n\n"
        "*Мониторинг (фон):*\n"
        "  • Порт-проб каждые 5 сек (фильтр 2/3)\n"
        "  • Авто-рестарт при падении ноды\n"
        "  • Ежедневный отчёт каждые 24ч",
        parse_mode="Markdown", reply_markup=MAIN_KEYBOARD,
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    if context.user_data.get("conv_state") is not None:
        await _input_handler(update, context)
        return

    text = update.message.text

    if text == "➕ Добавить юзера":
        context.user_data["conv_state"] = WAIT_CREATE
        await update.message.reply_text(
            "➕  *Создать юзера*\n\n"
            "`username` — базовый\n"
            "`username 30d` — срок 30 дней\n"
            "`username 30d 50gb` — + лимит 50 GB\n"
            "`username 30d 50gb 3dev` — + 3 устройства",
            parse_mode="Markdown",
        )
    elif text == "📅 Отчёт":
        await update.message.reply_text("⏳ Генерирую отчёт…")
        await update.message.reply_text(build_daily_report())
        for msg in check_expiry_warnings():
            await update.message.reply_text(msg)
        for msg in check_traffic_limit_warnings():
            await update.message.reply_text(msg)
    elif text == "🧠 OPS":
        await update.message.reply_text(format_status(), reply_markup=ops_keyboard())
    elif text == "👥 Юзеры":
        await update.message.reply_text("👥  *Управление пользователями*",
                                        parse_mode="Markdown", reply_markup=users_keyboard())
    elif text == "📊 Аналитика":
        await update.message.reply_text("📊  *Аналитика*",
                                        parse_mode="Markdown", reply_markup=analytics_keyboard())
    elif text == "🔔 Алерты":
        await update.message.reply_text(get_alert_status(),
                                        reply_markup=alerts_keyboard_with_state(_sched.daily_report_enabled))
    elif text == "⚙️ Настройки":
        nodes = api_get_nodes()
        ips   = sorted({n.get("ip", "") for n in nodes if n.get("ip")})
        await update.message.reply_text(
            "⚙️  *Настройки и действия*\n\n"
            f"📡  Нод в панели:  {len(nodes)}\n"
            f"🌐  Серверы:       {', '.join(ips) or '—'}\n"
            f"📅  Daily report:  {'✅' if _sched.daily_report_enabled else '❌'}",
            parse_mode="Markdown",
            reply_markup=settings_keyboard(_sched.daily_report_enabled),
        )
    else:
        await update.message.reply_text("Используй кнопки 👇", reply_markup=MAIN_KEYBOARD)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("confirm_delete_user_"):
        username = data[len("confirm_delete_user_"):]
        await query.edit_message_text(f"⏳ Удаляю {username}…")
        _, msg = delete_user(username)
        await query.edit_message_text(msg)
        return

    if data in ("cancel", "back_main"):
        context.user_data.clear()
        await query.edit_message_text("↩️ Отменено")
        return

    # ══ OPS ═══════════════════════════════════════════════════════════════════
    if data in ("ops_status", "ops_refresh"):
        await query.edit_message_text(format_status(), reply_markup=ops_keyboard())
    elif data == "ops_probe":
        await query.edit_message_text(get_probe_summary(), reply_markup=ops_keyboard())
    elif data == "ops_geo":
        await query.edit_message_text(get_geo_comparison(), reply_markup=ops_keyboard())
    elif data == "ops_server":
        await query.edit_message_text("🖥  Запрашиваю статистику серверов…")
        await query.edit_message_text(format_server_stats(), reply_markup=ops_keyboard())
    elif data == "ops_heal":
        await query.edit_message_text(
            "🚨  *Auto-Heal*\n\nПорт-монитор работает в фоне.\n"
            "При падении ноды авто-рестарт запускается автоматически.\n\n" + format_status(),
            parse_mode="Markdown", reply_markup=ops_keyboard(),
        )
    elif data == "ops_panic":
        await query.edit_message_text(
            "⚠️  *PANIC RESTART*\n\nStop → 2s → Start ALL сервисов.\n\nПодтверди:",
            parse_mode="Markdown", reply_markup=confirm_keyboard("panic", "all"),
        )
    elif data == "confirm_panic_all":
        await query.edit_message_text("💀  Выполняю panic restart…")
        await query.edit_message_text(panic_restart())
    elif data == "ops_ssh_menu":
        nodes = get_nodes_inline_list()
        context.user_data["conv_state"] = WAIT_SSH_NODE
        await query.edit_message_text("💻  *SSH-команда*\n\nВыбери ноду:",
                                      parse_mode="Markdown",
                                      reply_markup=node_picker_keyboard("ssh_node", nodes))
    elif data.startswith("ssh_node_"):
        parts   = data[len("ssh_node_"):].rsplit("_", 1)
        node_id = parts[0]
        context.user_data["ssh_target_node"] = node_id
        context.user_data["conv_state"] = WAIT_SSH_CMD
        await query.edit_message_text("💻  Введи bash-команду:")
    elif data == "ops_reboot_menu":
        await query.edit_message_text("♻️  *Ребут сервера*\n\nВыбери ноду:",
                                      parse_mode="Markdown",
                                      reply_markup=node_picker_keyboard("reboot_node", get_nodes_inline_list()))
    elif data.startswith("reboot_node_"):
        parts     = data[len("reboot_node_"):].rsplit("_", 1)
        node_id   = parts[0]
        names     = {nid: n for nid, n, _ in get_nodes_inline_list()}
        node_name = names.get(node_id, node_id)
        await query.edit_message_text(
            f"♻️  Перезагрузить сервер с *{node_name}*?",
            parse_mode="Markdown", reply_markup=confirm_keyboard("reboot_srv", node_id),
        )
    elif data.startswith("confirm_reboot_srv_"):
        node_id = data[len("confirm_reboot_srv_"):]
        await query.edit_message_text("♻️  Отправляю команду ребута…")
        _, msg = reboot_server(node_id)
        await query.edit_message_text(msg)

    # ══ USERS ══════════════════════════════════════════════════════════════════
    elif data == "users_list":
        await query.edit_message_text(format_users(), reply_markup=users_keyboard())
    elif data == "users_create":
        context.user_data["conv_state"] = WAIT_CREATE
        await query.edit_message_text(
            "➕  *Создать юзера*\n\n`username` — базовый\n`username 30d` — + срок\n"
            "`username 30d 50gb` — + лимит\n`username 30d 50gb 3dev` — + девайсы",
            parse_mode="Markdown",
        )
    elif data == "users_delete":
        context.user_data["conv_state"] = WAIT_DELETE
        await query.edit_message_text("🗑  *Удалить юзера*\n\nВведи имя:", parse_mode="Markdown")
    elif data == "users_disable":
        context.user_data["conv_state"] = WAIT_DISABLE
        await query.edit_message_text("🚫  *Отключить юзера*\n\nВведи имя:", parse_mode="Markdown")
    elif data == "users_enable":
        context.user_data["conv_state"] = WAIT_ENABLE
        await query.edit_message_text("✅  *Включить юзера*\n\nВведи имя:", parse_mode="Markdown")
    elif data == "users_info":
        context.user_data["conv_state"] = WAIT_INFO
        await query.edit_message_text("ℹ️  *Инфо о юзере*\n\nВведи имя:", parse_mode="Markdown")
    elif data == "users_reset_traffic":
        context.user_data["conv_state"] = WAIT_RESET_TRAFFIC
        await query.edit_message_text("🔄  *Сброс трафика*\n\nВведи имя:", parse_mode="Markdown")
    elif data == "users_set_limit":
        context.user_data["conv_state"] = WAIT_SET_LIMIT
        await query.edit_message_text("📦  *Установить лимит*\n\nФормат: `имя GB`\nПример: `john 50`",
                                      parse_mode="Markdown")
    elif data == "users_extend_expiry":
        context.user_data["conv_state"] = WAIT_EXTEND_EXPIRY
        await query.edit_message_text("📅  *Продлить срок*\n\nФормат: `имя дней`\nПример: `john 30`",
                                      parse_mode="Markdown")
    elif data == "users_set_devices":
        context.user_data["conv_state"] = WAIT_SET_DEVICES
        await query.edit_message_text("📱  *Лимит устройств*\n\nФормат: `имя количество`",
                                      parse_mode="Markdown")
    elif data == "users_sub":
        context.user_data["conv_state"] = WAIT_SUB
        await query.edit_message_text("🔗  *Ссылка подписки*\n\nВведи имя:", parse_mode="Markdown")
    elif data == "users_qr":
        context.user_data["conv_state"] = WAIT_QR
        await query.edit_message_text("📷  *QR-код*\n\nВведи имя:", parse_mode="Markdown")

    # ══ ANALYTICS ══════════════════════════════════════════════════════════════
    elif data == "analytics_traffic":
        await query.edit_message_text(traffic_stats(), reply_markup=analytics_keyboard())
    elif data == "analytics_fi":
        await query.edit_message_text(node_stats_by_pattern("fi"), reply_markup=analytics_keyboard())
    elif data == "analytics_de":
        await query.edit_message_text(node_stats_by_pattern("ge"), reply_markup=analytics_keyboard())
    elif data == "analytics_online":
        await query.edit_message_text(online_clients(), reply_markup=analytics_keyboard())
    elif data == "analytics_top":
        await query.edit_message_text(top_users_by_traffic(), reply_markup=analytics_keyboard())
    elif data == "analytics_chart_traffic":
        await query.edit_message_text("📊  Генерирую график трафика…")
        buf, err = traffic_chart(get_nodes_for_chart())
        if buf:
            await query.message.reply_photo(photo=buf, caption="📊 Node Traffic (GB)")
        else:
            await query.message.reply_text(err or "❌ Нет данных")
        await query.delete_message()
    elif data == "analytics_chart_latency":
        await query.edit_message_text("📉  Генерирую график латентности…")
        buf, err = latency_chart()
        if buf:
            await query.message.reply_photo(photo=buf, caption="📉 Latency Over Time")
        else:
            await query.message.reply_text(err or "❌ Данных пока нет — жди проб")
        await query.delete_message()

    # ══ SETTINGS ═══════════════════════════════════════════════════════════════
    elif data == "settings_discover":
        await query.edit_message_text("🔍  Ищу ноды в панели…")
        nodes = api_get_nodes()
        if not nodes:
            await query.edit_message_text("❌ Ноды не найдены — проверь PANEL_URL и API_KEY",
                                          reply_markup=settings_keyboard(_sched.daily_report_enabled))
            return
        lines = [f"✅  Найдено нод: {len(nodes)}\n"]
        for n in nodes:
            em = "🟢" if n.get("status") == "online" else "🔴"
            lines.append(f"{em} {n.get('flag','📡')} {n.get('name','?')} ({n.get('type','?')})")
        lines.append("\nВсе ноды загружены из панели.")
        await query.edit_message_text("\n".join(lines),
                                      reply_markup=settings_keyboard(_sched.daily_report_enabled))
    elif data == "action_restart_all":
        await query.edit_message_text("🔄  Перезапустить ВСЕ ноды?",
                                      reply_markup=confirm_keyboard("restart", "all"))
    elif data == "confirm_restart_all":
        await query.edit_message_text("🔄  Перезапускаю все ноды…")
        await query.edit_message_text(restart_all_nodes(),
                                      reply_markup=settings_keyboard(_sched.daily_report_enabled))
    elif data == "action_restart_hys":
        await query.edit_message_text("⚡  Перезапускаю Hysteria на всех нодах…")
        await query.edit_message_text("⚡  Hysteria Restart\n\n" + restart_by_name("", service="hysteria"),
                                      reply_markup=settings_keyboard(_sched.daily_report_enabled))
    elif data == "action_restart_vless":
        await query.edit_message_text("🌐  Перезапускаю VLESS на всех нодах…")
        await query.edit_message_text("🌐  VLESS Restart\n\n" + restart_by_name("", service="vless"),
                                      reply_markup=settings_keyboard(_sched.daily_report_enabled))
    elif data.startswith("action_restart_node_"):
        node_id = data[len("action_restart_node_"):]
        nodes   = api_get_nodes()
        node    = next((n for n in nodes if n["_id"] == node_id), None)
        name    = node.get("name", node_id) if node else node_id
        await query.edit_message_text(f"🔄  Перезапускаю {name}…")
        result  = restart_by_name(name)
        await query.edit_message_text(f"🔄 {name}\n\n{result}",
                                      reply_markup=settings_keyboard(_sched.daily_report_enabled))
    elif data == "action_sync":
        await query.edit_message_text("🔁  Синхронизирую ноды…")
        r   = api_sync()
        msg = "✅  Синхронизация запущена" if "error" not in r else f"❌  Ошибка: {r['error']}"
        await query.edit_message_text(msg, reply_markup=settings_keyboard(_sched.daily_report_enabled))
    elif data == "action_backup":
        await query.edit_message_text("💾  Снимаю бэкап конфигов…")
        files, summary = backup_all()
        await query.edit_message_text(f"💾  BACKUP\n\n{summary}")
        for f in files:
            try:
                with open(f, "rb") as fh:
                    await query.message.reply_document(document=fh, filename=f)
            except Exception:
                pass
            cleanup_backup(f)
    elif data == "action_reinstall_menu":
        await query.edit_message_text("🔧  *Переустановить ноду*\n\nВыбери:",
                                      parse_mode="Markdown",
                                      reply_markup=reinstall_keyboard(get_nodes_inline_list()))
    elif data.startswith("reinstall_"):
        parts = data[len("reinstall_"):].rsplit("_", 1)
        if len(parts) == 2:
            node_id, ntype = parts
            await query.edit_message_text(
                f"⚠️  Переустановить *{ntype.upper()}* на этой ноде?",
                parse_mode="Markdown",
                reply_markup=confirm_keyboard(f"reinstall_{ntype}", node_id),
            )
    elif data.startswith("confirm_reinstall_"):
        rest = data[len("confirm_reinstall_"):]
        for ntype in ("hysteria", "xray"):
            if rest.startswith(ntype + "_"):
                node_id = rest[len(ntype) + 1:]
                await query.edit_message_text(f"🔧  Переустанавливаю {ntype}…")
                ok, msg = reinstall_node(node_id, ntype)
                await query.edit_message_text(msg, parse_mode="Markdown")
                break

    # ══ ALERTS ═════════════════════════════════════════════════════════════════
    elif data == "alerts_status":
        await query.edit_message_text(get_alert_status(),
                                      reply_markup=alerts_keyboard_with_state(_sched.daily_report_enabled))
    elif data == "alerts_report_now":
        await query.edit_message_text("📅  Генерирую отчёт…")
        await query.message.reply_text(build_daily_report())
        for msg in check_expiry_warnings():
            await query.message.reply_text(msg)
        for msg in check_traffic_limit_warnings():
            await query.message.reply_text(msg)
        await query.delete_message()
    elif data == "alerts_mute_1":
        mute_alerts(1)
        await query.edit_message_text("🔇  Mute 1ч",
                                      reply_markup=alerts_keyboard_with_state(_sched.daily_report_enabled))
    elif data == "alerts_mute_3":
        mute_alerts(3)
        await query.edit_message_text("🔇  Mute 3ч",
                                      reply_markup=alerts_keyboard_with_state(_sched.daily_report_enabled))
    elif data == "alerts_mute_6":
        mute_alerts(6)
        await query.edit_message_text("🔇  Mute 6ч",
                                      reply_markup=alerts_keyboard_with_state(_sched.daily_report_enabled))
    elif data == "alerts_unmute":
        unmute_alerts()
        await query.edit_message_text("🔔  Алерты включены",
                                      reply_markup=alerts_keyboard_with_state(_sched.daily_report_enabled))
    elif data == "alerts_toggle_daily":
        _sched.daily_report_enabled = not _sched.daily_report_enabled
        state = "✅ включён" if _sched.daily_report_enabled else "❌ выключен"
        await query.edit_message_text(f"📅  Ежедневный отчёт: {state}",
                                      reply_markup=alerts_keyboard_with_state(_sched.daily_report_enabled))


async def _input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("conv_state")
    text  = update.message.text.strip()

    if text in _SECTION_BUTTONS:
        context.user_data.clear()
        await menu_handler(update, context)
        return

    context.user_data["conv_state"] = None

    if state == WAIT_SSH_NODE:
        await update.message.reply_text("👆  Выбери ноду кнопкой выше", reply_markup=MAIN_KEYBOARD)
        return

    if state == WAIT_SSH_CMD:
        node_id = context.user_data.get("ssh_target_node")
        if not node_id:
            await update.message.reply_text("❌  Нода не выбрана")
            return
        await update.message.reply_text(f"💻  Выполняю: `{text}`", parse_mode="Markdown")
        out = ssh_command(node_id, text)
        if len(out) > 3800:
            out = out[:3800] + "\n… (обрезано)"
        await update.message.reply_text(f"```\n{out}\n```", parse_mode="Markdown")
        return

    if state == WAIT_CREATE:
        parts    = text.split()
        username = parts[0]
        days  = next((int(re.sub(r"[^\d]", "", p)) for p in parts[1:] if "d" in p.lower()), 0)
        gb    = next((float(re.sub(r"[^\d.]", "", p)) for p in parts[1:] if "gb" in p.lower()), 0.0)
        dev   = next((int(re.sub(r"[^\d]", "", p)) for p in parts[1:] if "dev" in p.lower()), 0)
        await update.message.reply_text(f"⏳  Создаю юзера: {username}…")
        _, msg = create_user(username, traffic_limit_gb=int(gb), expire_days=days, max_devices=dev)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=users_keyboard())
    elif state == WAIT_DELETE:
        await update.message.reply_text(
            f"⚠️  Удалить *{text}*?\nДействие необратимо.", parse_mode="Markdown",
            reply_markup=confirm_keyboard("delete_user", text),
        )
    elif state == WAIT_DISABLE:
        _, msg = disable_user(text)
        await update.message.reply_text(msg, reply_markup=users_keyboard())
    elif state == WAIT_ENABLE:
        _, msg = enable_user(text)
        await update.message.reply_text(msg, reply_markup=users_keyboard())
    elif state == WAIT_INFO:
        await update.message.reply_text(get_user_info(text), parse_mode="Markdown",
                                        reply_markup=users_keyboard())
    elif state == WAIT_RESET_TRAFFIC:
        await update.message.reply_text(f"⏳  Сбрасываю трафик: {text}…")
        _, msg = reset_user_traffic(text)
        await update.message.reply_text(msg, reply_markup=users_keyboard())
    elif state == WAIT_SET_LIMIT:
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌  Формат: `имя GB`", parse_mode="Markdown")
            return
        try:
            gb = float(parts[1])
        except ValueError:
            await update.message.reply_text("❌  Неверное значение GB")
            return
        _, msg = set_traffic_limit(parts[0], gb)
        await update.message.reply_text(msg, reply_markup=users_keyboard())
    elif state == WAIT_EXTEND_EXPIRY:
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌  Формат: `имя дней`", parse_mode="Markdown")
            return
        try:
            days = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌  Неверное количество дней")
            return
        _, msg = extend_expiry(parts[0], days)
        await update.message.reply_text(msg, reply_markup=users_keyboard())
    elif state == WAIT_SET_DEVICES:
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌  Формат: `имя количество`", parse_mode="Markdown")
            return
        try:
            cnt = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌  Неверное число устройств")
            return
        _, msg = set_max_devices(parts[0], cnt)
        await update.message.reply_text(msg, reply_markup=users_keyboard())
    elif state == WAIT_SUB:
        url = get_user_subscription(text)
        if url:
            await update.message.reply_text(f"🔗  *{text}*\n\n`{url}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌  Подписка не найдена: {text}")
    elif state == WAIT_QR:
        await update.message.reply_text(f"⏳  Генерирую QR для {text}…")
        qr_path, sub_url = get_user_qr(text)
        if qr_path:
            with open(qr_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f, caption=f"📷  *{text}*\n\n`{sub_url}`", parse_mode="Markdown",
                )
            cleanup_qr(qr_path)
        else:
            await update.message.reply_text(sub_url)
    else:
        await update.message.reply_text("Используй кнопки 👇", reply_markup=MAIN_KEYBOARD)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, (Conflict, NetworkError, TimedOut)):
        return
    if isinstance(err, BadRequest) and "message is not modified" in str(err).lower():
        return
    logging.error(f"[BOT] error: {err}", exc_info=err)


async def post_init(application: Application):
    asyncio.ensure_future(monitor(application, ADMIN_ID))


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_error_handler(error_handler)
    print("✅  BOT STARTED — Celerity C3 OPS Panel")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
