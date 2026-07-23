from aiogram.fsm.state import State, StatesGroup


class OrderFSM(StatesGroup):
    name = State()
    phone = State()
    service = State()
    comment = State()


class ChatFSM(StatesGroup):
    free = State()
