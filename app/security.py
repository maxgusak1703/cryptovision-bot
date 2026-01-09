from cryptography.fernet import Fernet
from app.config import settings

cipher = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_key(text: str) -> str:
    return cipher.encrypt(text.encode()).decode() if text else None

def decrypt_key(text: str) -> str:
    return cipher.decrypt(text.encode()).decode() if text else None