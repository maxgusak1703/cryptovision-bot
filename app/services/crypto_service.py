import ccxt.async_support as ccxt
from app.security import decrypt_key
import logging

async def get_exchange_balance(exchange_name: str, key: str, secret: str, pas: str = None, is_demo: bool = False):
    modes_to_try = [is_demo, not is_demo]
    for mode in modes_to_try:
        try:
            ex_class = getattr(ccxt, exchange_name)
            config = {
                'apiKey': decrypt_key(key),
                'secret': decrypt_key(secret),
                'enableRateLimit': True,
                'timeout': 15000
            }
            
            d_pas = decrypt_key(pas)
            if d_pas and d_pas.lower() not in ["none", ""]:
                config['password'] = d_pas

            exchange = ex_class(config)
            if mode: exchange.set_sandbox_mode(True)

            async with exchange:
                balance = await exchange.fetch_balance()
                return {k: v for k, v in balance.get('total', {}).items() if v > 0}
        except Exception as e:
            if "invalid" in str(e).lower() or "50101" in str(e): continue
            return {"error": str(e)}
    return {"error": "Не вдалося підключитися"}