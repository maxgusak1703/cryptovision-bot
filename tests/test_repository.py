import pytest
from app.repositories.user_repo import UserRepository
from app.models import User, ExchangeAccount

@pytest.mark.asyncio
async def test_create_user_if_not_exists(db_session):
    repo = UserRepository(db_session)
    
    user = await repo.create_user_if_not_exists(12345, "test_user")
    assert user.id == 12345
    assert user.username == "test_user"
    
    user2 = await repo.create_user_if_not_exists(12345, "new_name")
    assert user2.id == user.id
    assert user2.username == "test_user" 

@pytest.mark.asyncio
async def test_add_and_get_accounts(db_session):
    repo = UserRepository(db_session)
    await repo.create_user_if_not_exists(1, "trader")
    
    acc = await repo.add_account(
        user_id=1,
        exchange_name="binance",
        api_key="encrypted_key",
        api_secret="encrypted_secret",
        api_passphrase=None,
        is_demo=False
    )
    
    assert acc.id is not None
    assert acc.exchange_name == "binance"
    
    accounts = await repo.get_user_accounts(1)
    assert len(accounts) == 1
    assert accounts[0].api_key == "encrypted_key"

@pytest.mark.asyncio
async def test_delete_account(db_session):
    repo = UserRepository(db_session)
    await repo.create_user_if_not_exists(99, "deleter")
    acc = await repo.add_account(99, "okx", "k", "s", None, True)
    
    result = await repo.delete_account(acc.id, 99)
    assert result is True
    
    accounts = await repo.get_user_accounts(99)
    assert len(accounts) == 0