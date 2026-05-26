import os
import paramiko
import time

SERVERS = {
    "GE": {
        "host": os.getenv("GE_HOST"),
        "user": os.getenv("GE_USER"),
        "password": os.getenv("GE_PASSWORD"),
    },
    "FI": {
        "host": os.getenv("FI_HOST"),
        "user": os.getenv("FI_USER"),
        "password": os.getenv("FI_PASSWORD"),
    },
}


def ssh_reboot(server_name: str) -> tuple[bool, str]:
    srv = SERVERS.get(server_name)
    if not srv:
        return False, f"❌ Сервер {server_name} не найден"

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=srv["host"],
            username=srv["user"],
            password=srv["password"],
            timeout=10,
        )
        client.exec_command("reboot")
        client.close()
        return True, f"✅ Команда reboot отправлена на {server_name} ({srv['host']})"
    except Exception as e:
        return False, f"❌ SSH ошибка {server_name}: {str(e)}"


def reboot_all() -> list[str]:
    results = []
    for name in SERVERS:
        ok, msg = ssh_reboot(name)
        results.append(msg)
        time.sleep(2)
    return results


def check_online(server_name: str, timeout: int = 120) -> bool:
    import socket
    srv = SERVERS.get(server_name)
    if not srv:
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = socket.create_connection((srv["host"], 22), timeout=3)
            sock.close()
            return True
        except Exception:
            time.sleep(5)
    return False
PYEOF
echo "OK"
