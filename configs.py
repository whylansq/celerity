import qrcode
import os


def generate_qr(text: str, filename: str = "qr.png") -> str:
    img = qrcode.make(text)
    img.save(filename)
    return filename


def cleanup_qr(filename: str):
    try:
        if filename and os.path.exists(filename):
            os.remove(filename)
    except Exception:
        pass
