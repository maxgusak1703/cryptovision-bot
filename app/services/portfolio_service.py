import asyncio
from app.repositories.user_repo import UserRepository
from app.services.crypto_service import CryptoService

class PortfolioService:
    def __init__(self, user_repo: UserRepository):
        self.repo = user_repo

    async def get_full_portfolio(self, user_id: int):
        accounts = await self.repo.get_user_accounts(user_id)
        if not accounts:
            return {}, []

        tasks = []
        for acc in accounts:
            tasks.append(CryptoService.get_balance(
                acc.exchange_name, 
                acc.api_key, 
                acc.api_secret, 
                acc.api_passphrase, 
                acc.is_demo
            ))
        
        results = await asyncio.gather(*tasks)
        
        detailed_portfolio = {}
        errors = []
        
        for acc, res in zip(accounts, results):
            mode_str = "Demo" if acc.is_demo else "Real"
            label = f"{acc.exchange_name.upper()} ({mode_str})"
            
            if "error" in res:
                errors.append(f"❌ {label}: {res['error']}")
            else:
                detailed_portfolio[label] = res
                
        return detailed_portfolio, errors