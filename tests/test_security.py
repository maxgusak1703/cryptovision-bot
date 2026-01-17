from cryptography.fernet import Fernet
from app.security import encrypt_key, decrypt_key

def test_encryption_decryption_cycle():

    original_api_key = "test_binance_key_123"
    ciper = Fernet(Fernet.generate_key())
    encrypted = encrypt_key(original_api_key, ciper)
    decrypted = decrypt_key(encrypted, ciper)

    assert decrypted == original_api_key
    assert encrypted != original_api_key