from aiogram.fsm.state import State, StatesGroup


class UserFlow(StatesGroup):
    waiting_topup_amount = State()
    waiting_receipt = State()

class AdminFlow(StatesGroup):
    create_plan_name = State()
    create_plan_duration = State()
    create_plan_traffic_gb = State()
    create_plan_price = State()
    create_pm_name = State()
    create_pm_instructions = State()
    create_pm_card_numbers = State()
    openvpn_endpoint_port = State()
