from aiogram.fsm.state import State, StatesGroup

class AddExchange(StatesGroup):
    waiting_for_name = State()
    waiting_for_key = State()
    waiting_for_secret = State()
    waiting_for_passphrase = State()
    waiting_for_mode = State()

class AIChat(StatesGroup):
    waiting_for_question = State()