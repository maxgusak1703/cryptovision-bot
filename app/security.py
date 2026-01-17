from cryptography.fernet import Fernet
from app.config import settings

cipher = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_key(text: str, cipher: Fernet = None) -> str:
    cipher = cipher or Fernet(settings.ENCRYPTION_KEY.encode())
    return cipher.encrypt(text.encode()).decode() if text else None

def decrypt_key(text: str, cipher: Fernet = None) -> str:
    cipher = cipher or Fernet(settings.ENCRYPTION_KEY.encode())
    return cipher.decrypt(text.encode()).decode() if text else None