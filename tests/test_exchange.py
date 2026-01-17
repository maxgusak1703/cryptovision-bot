import pytest
from unittest.mock import AsyncMock 

async def calculate_total_usd(exchange_instance):
    balance = await exchange_instance.fetch_balance()
    total = 0
    for coin, amount in balance['total'].items():
        if coin == 'USDT':
            total += amount
    return total

@pytest.mark.asyncio
async def test_calculate_total_usd_with_mock():
    mock_exchange = AsyncMock()
    
    mock_exchange.fetch_balance.return_value = {
        'total': {'USDT': 100.0, 'BTC': 0.5}
    }

    result = await calculate_total_usd(mock_exchange)

    assert result == 100.0
    mock_exchange.fetch_balance.assert_called_once()


