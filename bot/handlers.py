import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.security import encrypt_key, decrypt_key
from app.services.ai_service import get_gemini_advice

from app.repositories.user_repo import UserRepository
from app.services.portfolio_service import PortfolioService

router = Router()
logger = logging.getLogger(__name__)

SUPPORTED_EXCHANGES = ["binance", "bybit", "okx", "kucoin", "bitget"]

# --- Хендлери команд ---

@router.message(Command("start"))
async def cmd_start(message: types.Message, session: AsyncSession):

    repo = UserRepository(session)
    await repo.create_user_if_not_exists(message.from_user.id, message.from_user.username)
    
    await message.answer(
        "🛡 CryptoVision AI працює!\nЯ готовий моніторити ваші активи.", 
        reply_markup=get_main_kb(), 
        parse_mode="Markdown"
    )

@router.message(F.text == "👤 Профіль")
async def cmd_profile(message: types.Message, session: AsyncSession):
    repo = UserRepository(session)
    accounts = await repo.get_user_accounts(message.from_user.id)
    
    if not accounts:
        return await message.answer("🔌 Біржі ще не підключені.", reply_markup=get_main_kb())
    
    acc_data = []
    text = "👤 Ваші підключення:\n"
    
    for acc in accounts:
        raw_key = decrypt_key(acc.api_key)
        mask = f"{raw_key[:4]}...{raw_key[-4:]}" if len(raw_key) > 8 else "***"
        
        mode_str = "🧪 Demo" if acc.is_demo else "✅ Real"
        text += f"• {acc.exchange_name.upper()} `[{mask}]` ({mode_str})\n"
        acc_data.append((acc, mask))
        
    await message.answer(text, reply_markup=get_profile_kb(acc_data), parse_mode="Markdown")

@router.message(F.text == "📊 Мій баланс")
async def handle_balance(message: types.Message, session: AsyncSession):
    status_msg = await message.answer("⏳ Збираю дані з бірж...")
    
    repo = UserRepository(session)
    service = PortfolioService(repo)
    
    detailed, errors = await service.get_full_portfolio(message.from_user.id)
    
    if errors:
        await message.answer("⚠️ Є зауваження:\n" + "\n".join(errors))
        
    if not detailed:
        return await status_msg.edit_text("🤷‍♂️ Портфель порожній або помилка з'єднання.")
        
    res_text = "💰 Детальний баланс:\n"
    total_usd = 0.0
    
    for label, data in detailed.items():
        if "error" in data: continue 
        
        res_text += f"\n🏛 **{label}**\n"
        subtotal = 0.0
        
        sorted_assets = sorted(data.items(), key=lambda x: x[1]['usd_val'], reverse=True)
        
        for coin, info in sorted_assets:
            amt, usd = info["amount"], info["usd_val"]
            subtotal += usd
            res_text += f"  🔹 {coin}: `{amt:.4f}` (~${usd:.2f})\n"
                
        res_text += f"  Разом: `${subtotal:.2f}`\n"
        total_usd += subtotal
        
    res_text += f"\n══════════════\n💵 ВСЬОГО: `${total_usd:.2f}`"
    
    await status_msg.edit_text(res_text, parse_mode="Markdown")

# --- AI Logic ---

@router.message(F.text == "🤖 AI Порада")
async def ai_ask(message: types.Message, state: FSMContext):
    await message.answer("🤖 Напишіть ваше запитання до ШІ (наприклад, 'Чи варто зараз купувати BTC?'):")
    await state.set_state(AIChat.waiting_for_question)

@router.message(AIChat.waiting_for_question)
async def ai_handle_question(message: types.Message, state: FSMContext, session: AsyncSession):
    status_msg = await message.answer("🧠 ШІ аналізує ваш портфель...")
    
    repo = UserRepository(session)
    service = PortfolioService(repo)
    detailed, _ = await service.get_full_portfolio(message.from_user.id)
    
    assets_str_parts = []
    for label, assets in detailed.items():
        if "error" in assets: continue
        coins_info = ", ".join([f"{c}: {d['amount']:.4f} (${d['usd_val']:.2f})" for c, d in assets.items()])
        assets_str_parts.append(f"[{label}: {coins_info}]")
    
    assets_str = "; ".join(assets_str_parts) if assets_str_parts else "Портфель порожній"
    
    try:
        answer = await get_gemini_advice(message.text, assets_str)
        await status_msg.edit_text(f"📜 Аналітика:\n\n{answer}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await status_msg.edit_text("❌ Помилка з'єднання з AI.")
    finally:
        await state.clear()

# --- FSM: Додавання біржі ---

@router.message(F.text == "🔌 Додати біржу")
@router.callback_query(F.data == "add_new")
async def add_start(event: types.Message | types.CallbackQuery, state: FSMContext):
    msg = event if isinstance(event, types.Message) else event.message
    if isinstance(event, types.CallbackQuery): await event.answer()
    
    await msg.answer("Оберіть біржу:", reply_markup=get_exchange_kb())
    await state.set_state(AddExchange.waiting_for_name)

@router.message(F.text == "❌ Скасувати додавання")
async def cancel_add(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.", reply_markup=get_main_kb())

@router.message(AddExchange.waiting_for_name)
async def add_name(message: types.Message, state: FSMContext):
    name = message.text.lower().strip()
    if name not in SUPPORTED_EXCHANGES:
        return await message.answer("❌ Оберіть біржу з кнопок внизу!", reply_markup=get_exchange_kb())
    
    await state.update_data(name=name)
    await message.answer("Оберіть режим підключення:", reply_markup=get_mode_kb())
    await state.set_state(AddExchange.waiting_for_mode)

@router.message(AddExchange.waiting_for_mode)
async def add_mode(message: types.Message, state: FSMContext):
    is_demo = "Demo" in message.text
    await state.update_data(is_demo=is_demo)
    
    mode_text = "SandBox/Demo" if is_demo else "REAL TRADING"
    await message.answer(f"Обрано режим: {mode_text}\n\nВведіть API Key:", reply_markup=get_cancel_kb(), parse_mode="Markdown")
    await state.set_state(AddExchange.waiting_for_key)

@router.message(AddExchange.waiting_for_key)
async def add_key(message: types.Message, state: FSMContext):
    await state.update_data(key=message.text.strip())
    await message.delete() 
    await message.answer("Введіть API Secret:", reply_markup=get_cancel_kb())
    await state.set_state(AddExchange.waiting_for_secret)

@router.message(AddExchange.waiting_for_secret)
async def add_secret(message: types.Message, state: FSMContext):
    await state.update_data(secret=message.text.strip())
    await message.delete()
    await message.answer("Введіть Passphrase (якщо є, або натисніть 'Пропустити'):", reply_markup=get_skip_kb())
    await state.set_state(AddExchange.waiting_for_passphrase)

@router.message(AddExchange.waiting_for_passphrase)
async def add_pass(message: types.Message, state: FSMContext, session: AsyncSession):
    txt = message.text.lower()
    passphrase = None
    if txt not in ["пропустити", "ні", "немає", "➡️ пропустити (якщо не потрібно)"]:
        passphrase = message.text.strip()
        await message.delete()

    data = await state.get_data()
    
    enc_key = encrypt_key(data['key'])
    enc_secret = encrypt_key(data['secret'])
    enc_pass = encrypt_key(passphrase) if passphrase else None
    
    repo = UserRepository(session)
    await repo.add_account(
        user_id=message.from_user.id,
        exchange_name=data['name'],
        api_key=enc_key,
        api_secret=enc_secret,
        api_passphrase=enc_pass,
        is_demo=data['is_demo']
    )
    
    await message.answer(f"✅ Біржу {data['name'].upper()} успішно додано!", reply_markup=get_main_kb(), parse_mode="Markdown")
    await state.clear()

# --- Видалення даних ---

@router.callback_query(F.data.startswith("del_ex_"))
async def delete_exchange_callback(callback: types.CallbackQuery, session: AsyncSession):
    ex_id = int(callback.data.split("_")[2])
    repo = UserRepository(session)
    
    success = await repo.delete_account(ex_id, callback.from_user.id)
    
    if success:
        await callback.answer("Видалено!")
        await callback.message.edit_text("✅ Біржу успішно видалено.")
    else:
        await callback.answer("Помилка видалення", show_alert=True)

@router.message(F.text == "🗑 Скинути всі дані")
async def confirm_delete_start(message: types.Message):
    await message.answer("⚠️ Ви впевнені? Це видалить усі підключені біржі та ваш профіль.", reply_markup=get_confirm_delete_kb())

@router.message(F.text == "❌ Так, видалити все")
async def process_full_delete(message: types.Message, session: AsyncSession):
    repo = UserRepository(session)
    await repo.delete_all_user_data(message.from_user.id)
    
    await message.answer("💨 Всі дані видалено. Бот перезавантажено.", reply_markup=types.ReplyKeyboardRemove())