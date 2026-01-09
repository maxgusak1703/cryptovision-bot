import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import ccxt.async_support as ccxt

from bot.states import AddExchange, AIChat
from bot.keyboards import (
    get_main_kb, 
    get_exchange_kb, 
    get_mode_kb, 
    get_profile_kb, 
    get_confirm_delete_kb,
    get_cancel_kb,
    get_skip_kb
)
from app.database import SessionLocal
from app.models import User, ExchangeAccount
from app.security import encrypt_key, decrypt_key
from app.services.crypto_service import get_exchange_balance
from app.services.ai_service import get_gemini_advice

router = Router()
logger = logging.getLogger(__name__)

SUPPORTED_EXCHANGES = ["binance", "bybit", "okx", "kucoin", "bitget"]

async def get_detailed_portfolio_with_prices(user_id: int):
    with SessionLocal() as db:
        accounts = db.query(ExchangeAccount).filter_by(owner_id=user_id).all()
        account_list = [
            {
                "name": acc.exchange_name,
                "key": acc.api_key,
                "secret": acc.api_secret,
                "pass": acc.api_passphrase,
                "is_demo": acc.is_demo
            } for acc in accounts
        ]

    detailed_portfolio = {}
    errors = []

    for acc in account_list:
        res = await get_exchange_balance(
            acc["name"], acc["key"], acc["secret"], acc["pass"], acc["is_demo"]
        )
        
        mode_str = "Demo" if acc["is_demo"] else "Real"
        label = f"{acc['name'].upper()} ({mode_str})"
        
        if isinstance(res, dict) and "error" not in res:
            try:
                ex_class = getattr(ccxt, acc["name"])
                exchange = ex_class()
                symbols = [f"{coin}/USDT" for coin in res.keys() if coin != 'USDT']
                tickers = {}
                if symbols:
                    try:
                        tickers = await exchange.fetch_tickers(symbols)
                    except:
                        pass
                
                await exchange.close()
                
                assets_with_usd = {}
                for coin, amount in res.items():
                    price = 1.0
                    if coin != 'USDT':
                        t = tickers.get(f"{coin}/USDT") or tickers.get(f"{coin}/USD")
                        price = t['last'] if t and 'last' in t else 0.0
                    
                    assets_with_usd[coin] = {"amount": amount, "usd_val": amount * price}
                detailed_portfolio[label] = assets_with_usd
            except Exception as e:
                detailed_portfolio[label] = {k: {"amount": v, "usd_val": 0.0} for k, v in res.items()}
                logger.error(f"Error: {e}")
        else:
            errors.append(f"❌ {label}: {res.get('error', 'Error')}")
            
    return detailed_portfolio, errors

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == message.from_user.id).first()
        if not user:
            db.add(User(id=message.from_user.id, username=message.from_user.username))
            db.commit()
    await message.answer("🛡 **CryptoVision AI** активовано!", reply_markup=get_main_kb(), parse_mode="Markdown")

@router.message(F.text == "👤 Профіль")
async def cmd_profile(message: types.Message):
    with SessionLocal() as db:
        accounts = db.query(ExchangeAccount).filter_by(owner_id=message.from_user.id).all()
        if not accounts: return await message.answer("Біржі не підключені.")
        
        acc_data = []
        text = "👤 **Ваші підключення:**\n"
        for acc in accounts:
            raw_key = decrypt_key(acc.api_key)
            mask = f"{raw_key[:4]}...{raw_key[-4:]}"
            text += f"• {acc.exchange_name.upper()} `[{mask}]` ({'Demo' if acc.is_demo else 'Real'})\n"
            acc_data.append((acc, mask))
        await message.answer(text, reply_markup=get_profile_kb(acc_data), parse_mode="Markdown")

@router.callback_query(F.data.startswith("del_ex_"))
async def delete_exchange_callback(callback: types.CallbackQuery):
    ex_id = int(callback.data.split("_")[2])
    with SessionLocal() as db:
        acc = db.query(ExchangeAccount).filter_by(id=ex_id, owner_id=callback.from_user.id).first()
        if acc:
            db.delete(acc)
            db.commit()
            await callback.answer("Видалено!")
            await callback.message.edit_text("✅ Біржу успішно видалено.")

@router.message(F.text == "📊 Мій баланс")
async def handle_balance(message: types.Message):
    status_msg = await message.answer("⏳ Рахую баланс...")
    detailed, errors = await get_detailed_portfolio_with_prices(message.from_user.id)
    
    if errors: await message.answer("\n".join(errors))
    if not detailed: return await status_msg.edit_text("Портфель порожній.")
        
    res_text = "💰 **Детальний баланс:**\n"
    total_usd = 0.0
    for label, assets in detailed.items():
        res_text += f"\n🏛 **{label}**\n"
        subtotal = 0.0
        for coin, data in assets.items():
            amt, usd = data["amount"], data["usd_val"]
            subtotal += usd
            res_text += f"  🔹 {coin}: `{amt:.4f}` (~${usd:.2f})\n"
        res_text += f"  **Разом:** `${subtotal:.2f}`\n"
        total_usd += subtotal
    res_text += f"\n══════════════\n💵 **ВСЬОГО:** `${total_usd:.2f}`"
    await status_msg.edit_text(res_text, parse_mode="Markdown")

@router.message(F.text == "🤖 AI Порада")
async def ai_ask(message: types.Message, state: FSMContext):
    await message.answer("🤖 Напишіть ваше запитання до ШІ:")
    await state.set_state(AIChat.waiting_for_question)

@router.message(AIChat.waiting_for_question)
async def ai_handle_question(message: types.Message, state: FSMContext):
    status_msg = await message.answer("🧠 ШІ аналізує дані...")
    detailed, _ = await get_detailed_portfolio_with_prices(message.from_user.id)
    
    assets_parts = []
    for label, assets in detailed.items():
        coins_info = ", ".join([f"{c}: {d['amount']:.4f} (${d['usd_val']:.2f})" for c, d in assets.items()])
        assets_parts.append(f"[{label}: {coins_info}]")
    assets_str = "; ".join(assets_parts) if assets_parts else "Порожньо"
    
    try:
        answer = await get_gemini_advice(message.text, assets_str)
        await status_msg.edit_text(f"📜 **Аналітика:**\n\n{answer}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await status_msg.edit_text("❌ Помилка ШІ.")
    finally:
        await state.clear()

@router.message(F.text == "❌ Скасувати додавання")
async def cancel_add(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.", reply_markup=get_main_kb())

@router.message(F.text == "🔌 Додати біржу")
@router.callback_query(F.data == "add_new")
async def add_start(event: types.Message | types.CallbackQuery, state: FSMContext):
    msg = event if isinstance(event, types.Message) else event.message
    if isinstance(event, types.CallbackQuery): await event.answer()
    await msg.answer("Оберіть біржу:", reply_markup=get_exchange_kb())
    await state.set_state(AddExchange.waiting_for_name)

@router.message(AddExchange.waiting_for_name)
async def add_name(message: types.Message, state: FSMContext):
    name = message.text.lower().strip()
    if name not in SUPPORTED_EXCHANGES:
        return await message.answer("❌ Оберіть з кнопок!", reply_markup=get_exchange_kb())
    await state.update_data(name=name)
    await message.answer("Оберіть режим:", reply_markup=get_mode_kb())
    await state.set_state(AddExchange.waiting_for_mode)

@router.message(AddExchange.waiting_for_mode)
async def add_mode(message: types.Message, state: FSMContext):
    await state.update_data(is_demo="Demo" in message.text)
    await message.answer("Введіть **API Key**:", reply_markup=get_cancel_kb(), parse_mode="Markdown")
    await state.set_state(AddExchange.waiting_for_key)

@router.message(AddExchange.waiting_for_key)
async def add_key(message: types.Message, state: FSMContext):
    await state.update_data(key=message.text.strip())
    await message.delete()
    await message.answer("Введіть **API Secret**:", reply_markup=get_cancel_kb())
    await state.set_state(AddExchange.waiting_for_secret)

@router.message(AddExchange.waiting_for_secret)
async def add_secret(message: types.Message, state: FSMContext):
    await state.update_data(secret=message.text.strip())
    await message.delete()
    await message.answer("Введіть **API Passphrase**:", reply_markup=get_skip_kb())
    await state.set_state(AddExchange.waiting_for_passphrase)

@router.message(AddExchange.waiting_for_passphrase)
async def add_pass(message: types.Message, state: FSMContext):
    txt = message.text.lower()
    val = None if "пропустити" in txt or txt in ["ні", "немає"] else message.text.strip()
    await state.update_data(passphrase=val)
    await message.delete()
    
    data = await state.get_data()
    with SessionLocal() as db:
        new_acc = ExchangeAccount(
            exchange_name=data['name'], is_demo=data['is_demo'],
            api_key=encrypt_key(data['key']), api_secret=encrypt_key(data['secret']),
            api_passphrase=encrypt_key(data['passphrase']) if data['passphrase'] else None,
            owner_id=message.from_user.id
        )
        db.add(new_acc)
        db.commit()
    await message.answer("✅ Готово!", reply_markup=get_main_kb())
    await state.clear()

@router.message(F.text == "🗑 Скинути всі дані")
async def confirm_delete_start(message: types.Message):
    await message.answer("⚠️ Видалити все безповоротно?", reply_markup=get_confirm_delete_kb())

@router.message(F.text == "❌ Так, видалити все")
async def process_full_delete(message: types.Message):
    with SessionLocal() as db:
        db.query(ExchangeAccount).filter_by(owner_id=message.from_user.id).delete()
        db.query(User).filter_by(id=message.from_user.id).delete()
        db.commit()
    await message.answer("💨 Дані видалено.", reply_markup=types.ReplyKeyboardRemove())