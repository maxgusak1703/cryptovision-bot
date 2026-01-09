from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import types

def get_main_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📊 Мій баланс"))
    builder.row(types.KeyboardButton(text="🔌 Додати біржу"))
    builder.row(types.KeyboardButton(text="🤖 AI Порада"))
    builder.row(types.KeyboardButton(text="👤 Профіль"))
    builder.row(types.KeyboardButton(text="🗑 Скинути всі дані"))
    return builder.as_markup(resize_keyboard=True)

def get_exchange_kb():
    builder = ReplyKeyboardBuilder()
    exchanges = ["Binance", "Bybit", "OKX", "KuCoin", "Bitget"]
    for ex in exchanges:
        builder.add(types.KeyboardButton(text=ex))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_mode_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="✅ Real Trading"), types.KeyboardButton(text="🧪 Demo / Sandbox"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_cancel_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Скасувати додавання"))
    return builder.as_markup(resize_keyboard=True)

def get_skip_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="➡️ Пропустити (якщо не потрібно)"))
    builder.row(types.KeyboardButton(text="❌ Скасувати додавання"))
    return builder.as_markup(resize_keyboard=True)

def get_profile_kb(accounts_with_masks):
    builder = InlineKeyboardBuilder()
    for acc, mask in accounts_with_masks:
        builder.row(types.InlineKeyboardButton(
            text=f"🗑 Видалити {acc.exchange_name.upper()} ({mask})",
            callback_data=f"del_ex_{acc.id}")
        )
    builder.row(types.InlineKeyboardButton(text="➕ Додати ще", callback_data="add_new"))
    return builder.as_markup()

def get_confirm_delete_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Так, видалити все"), types.KeyboardButton(text="🔙 Скасувати"))
    return builder.as_markup(resize_keyboard=True)