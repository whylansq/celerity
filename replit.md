# Personal OPS Telegram Bot

Telegram-бот для управления VPN-панелью Celerity C3 (4 ноды: FI HYS, FI VLESS, GE HYS, GE VLESS).

## Структура файлов

| Файл | Назначение |
|---|---|
| `main.py` | Главный файл: все хэндлеры, команды, роутинг |
| `keyboard.py` | Все клавиатуры (reply + inline) |
| `nodes.py` | Управление нодами: статус, рестарт, panic |
| `users.py` | Юзеры: создание, удаление, лимиты, QR |
| `traffic.py` | Аналитика трафика |
| `alerts.py` | Мониторинг в фоне: ноды, трафик, API |
| `scheduler.py` | Ежедневный отчёт, алерты ресурсов/юзеров |
| `server.py` | SSH-статистика серверов (CPU/RAM/Disk) |
| `prober.py` | Async TCP-проб с фильтром 2/3 |
| `charts.py` | Графики трафика и латентности |
| `backup.py` | Бэкап конфигов нод, переустановка |
| `configs.py` | Генерация QR-кодов |
| `mcp.py` | HTTP-клиент к MCP API |
| `install.sh` | Установка на сервер (Ubuntu/Debian) |

## Переменные окружения (.env)

```
BOT_TOKEN=     # токен от @BotFather
ADMIN_ID=      # твой Telegram user_id
API_KEY=       # API-ключ панели
MCP_URL=       # https://whitelist.soon.it/api/mcp
```

## Пользовательские предпочтения

- Язык общения: русский
- Проект личный, некоммерческий
- Кнопки внизу — основная навигация (не /команды)
