"""
FSM состояния для бота
"""
from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    """Состояния при добавлении/привязке клиента"""
    # Добавление нового клиента
    waiting_for_contract_start = State()
    waiting_for_contract_months = State()
    waiting_for_contact = State()
    # Привязка клиента к существующей записи (админ)
    waiting_link_username = State()
    waiting_link_select = State()
