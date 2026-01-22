import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.crypto_service import CryptoService
from app.services.portfolio_service import PortfolioService
from app.models import ExchangeAccount

# --- Тест CryptoService ---

@pytest.mark.asyncio
async def test_crypto_service_get_balance():
    with patch("app.services.crypto_service.ccxt") as mock_ccxt:
        with patch("app.services.crypto_service.decrypt_key", side_effect=lambda x: x):
            
            mock_exchange = AsyncMock()
            mock_exchange.fetch_balance.return_value = {
                'total': {'BTC': 1.0, 'USDT': 100.0, 'XRP': 0.0}
            }
            mock_exchange.fetch_tickers.return_value = {
                'BTC/USDT': {'last': 50000.0}
            }
            
            mock_ex_class = MagicMock(return_value=mock_exchange)
            setattr(mock_ccxt, "binance", mock_ex_class)

            result = await CryptoService.get_balance("binance", "key", "secret")
            
            assert "error" not in result
            assert "BTC" in result
            assert result["BTC"]["amount"] == 1.0
            assert result["BTC"]["usd_val"] == 50000.0
            
            assert "USDT" in result
            assert result["USDT"]["usd_val"] == 100.0
            assert "XRP" not in result  # Нульові баланси ігноруються
            

# --- Тест PortfolioService ---

@pytest.mark.asyncio
async def test_portfolio_service_full_flow():
    mock_repo = AsyncMock()
    mock_repo.get_user_accounts.return_value = [
        ExchangeAccount(exchange_name="binance", api_key="k", api_secret="s", is_demo=False),
        ExchangeAccount(exchange_name="bybit", api_key="k2", api_secret="s2", is_demo=True)
    ]
    
    def async_return(result):
        f = asyncio.Future()
        f.set_result(result)
        return f

    with patch("app.services.portfolio_service.CryptoService") as MockCryptoService:

        MockCryptoService.get_balance.side_effect = [
            async_return({"USDT": {"amount": 100, "usd_val": 100}}), # Binance результат
            async_return({"error": "Invalid API Key"})               # Bybit помилка
        ]
        
        service = PortfolioService(mock_repo)
        detailed, errors = await service.get_full_portfolio(user_id=1)
        
        assert "BINANCE (Real)" in detailed
        assert detailed["BINANCE (Real)"]["USDT"]["usd_val"] == 100
        
        assert len(errors) == 1
        assert "BYBIT (Demo)" in errors[0]