"""
FSM состояния для бота
"""
from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    """Состояния при добавлении клиента"""
    waiting_for_contract_start = State()
    waiting_for_contract_months = State()
    waiting_for_contact = State()
