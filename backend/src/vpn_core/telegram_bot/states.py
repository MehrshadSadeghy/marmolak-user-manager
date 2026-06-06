from aiogram.fsm.state import State, StatesGroup


class UserFlow(StatesGroup):
    waiting_topup_amount = State()
    waiting_receipt = State()
