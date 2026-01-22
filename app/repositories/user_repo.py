from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, ExchangeAccount

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user_if_not_exists(self, telegram_id: int, username: str) -> User:
        stmt = select(User).where(User.id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(id=telegram_id, username=username)
            self.session.add(user)
            await self.session.commit()
        return user

    async def get_user_accounts(self, user_id: int) -> list[ExchangeAccount]:
        stmt = select(ExchangeAccount).where(ExchangeAccount.owner_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_account(self, user_id: int, exchange_name: str, api_key: str, api_secret: str, api_passphrase: str | None, is_demo: bool) -> ExchangeAccount:
        new_acc = ExchangeAccount(
            exchange_name=exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
            is_demo=is_demo,
            owner_id=user_id
        )
        self.session.add(new_acc)
        await self.session.commit()
        return new_acc

    async def delete_account(self, account_id: int, user_id: int) -> bool:
        stmt = select(ExchangeAccount).where(ExchangeAccount.id == account_id, ExchangeAccount.owner_id == user_id)
        result = await self.session.execute(stmt)
        acc = result.scalars().first()
        
        if acc:
            await self.session.delete(acc)
            await self.session.commit()
            return True
        return False

    async def delete_all_user_data(self, user_id: int):
        """Видаляє користувача та всі його біржі."""
        stmt_acc = delete(ExchangeAccount).where(ExchangeAccount.owner_id == user_id)
        await self.session.execute(stmt_acc)
        
        stmt_user = delete(User).where(User.id == user_id)
        await self.session.execute(stmt_user)
        
        await self.session.commit()