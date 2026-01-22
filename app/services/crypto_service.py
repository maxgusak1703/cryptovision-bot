import asyncio
import ccxt.async_support as ccxt
from app.security import decrypt_key

class CryptoService:
    @staticmethod
    async def get_balance(exchange_name: str, key: str, secret: str, pas: str = None, is_demo: bool = False):
        exchange = None
        try:
            ex_class = getattr(ccxt, exchange_name)
            config = {
                'apiKey': decrypt_key(key),
                'secret': decrypt_key(secret),
                'enableRateLimit': True,
                'timeout': 20000 
            }
            
            d_pas = decrypt_key(pas)
            if d_pas and d_pas.lower() not in ["none", ""]:
                config['password'] = d_pas

            exchange = ex_class(config)
            
            if is_demo:
                exchange.set_sandbox_mode(True)

            async with exchange:
                balance_resp = await exchange.fetch_balance()
                assets = {k: v for k, v in balance_resp.get('total', {}).items() if v > 0}
                
                if not assets:
                    return {}

                assets_with_usd = {}
                symbols_to_fetch = []
                
                for coin in assets.keys():
                    if coin != 'USDT' and coin != 'USD':
                        symbols_to_fetch.append(f"{coin}/USDT")

                tickers = {}
                if symbols_to_fetch:
                    try:
                        tickers = await exchange.fetch_tickers(symbols_to_fetch)
                    except Exception as e:
                        print(f"Error fetching tickers for {exchange_name}: {e}")
           
                for coin, amount in assets.items():
                    price = 0.0
                    
                    if coin == 'USDT' or coin == 'USD':
                        price = 1.0
                    else:
                        pair = f"{coin}/USDT"
                        if pair in tickers and 'last' in tickers[pair]:
                             price = tickers[pair]['last']
                        elif f"{coin}/USD" in tickers and 'last' in tickers[f"{coin}/USD"]:
                             price = tickers[f"{coin}/USD"]['last'] 
                    
                    usd_val = amount * price
                    
                    assets_with_usd[coin] = {
                        "amount": amount,
                        "usd_val": usd_val
                    }

                return assets_with_usd
                
        except Exception as e:
            return {"error": str(e)}
        finally:
            if exchange:
                await exchange.close()