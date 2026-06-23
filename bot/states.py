from aiogram.dispatcher.filters.state import State, StatesGroup


class Registration(StatesGroup):
    """Регистрация пользователя при подаче заявки."""
    name = State()
    phone = State()
    city = State()


class AddObject(StatesGroup):
    """Создание нового объекта аренды (админ)."""
    name = State()
    price = State()
    description = State()
    photo = State()
    confirm = State()


class EditObject(StatesGroup):
    """Редактирование существующего объекта."""
    field = State()
    value = State()
