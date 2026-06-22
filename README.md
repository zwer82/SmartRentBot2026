# 🏠 SmartRentBot

Telegram-бот для управления арендой жилья. Построен на **aiogram 2.25.1** с интеграцией **Google Sheets**.

---

## ✨ Возможности

### Для пользователей
- **Каталог объектов** — просмотр доступных квартир/домов с фото
- **Подача заявок** — после просмотра объекта можно оставить заявку
- **Статусы заявок** — отслеживание: 🆕 Новый → 🟡 В обработке → 🟢 Подтверждён → 🔵 Завершён / 🔴 Отменён
- **Мои заявки** — список всех заявок пользователя
- **Профиль** — данные из последней заявки

### Для администраторов
- **Админ-панель** с inline-кнопками
- **Управление объектами** — CRUD с загрузкой фото
- **Управление заявками** — фильтр по статусу, смена статуса
- **Рассылка** — отправка сообщений всем пользователям

### Системные
- Google Sheets как база данных (заявки + объекты)
- Проверка дубликатов по Telegram ID и телефону
- Уведомление админу при новой заявке
- Уведомление пользователю при смене статуса
- Webhook-режим для Railway + polling для локальной разработки

---

## 🚀 Быстрый старт (локально)

### 1. Клонируйте и установите

```bash
cd smartrent_bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройте Google Sheets

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите **Google Sheets API** и **Google Drive API**
3. Создайте сервисный аккаунт → скачайте `credentials.json`
4. Поместите `credentials.json` в корень проекта
5. Создайте **Google Таблицу** и скопируйте её ID (из URL `/d/.../edit`)
6. Дайте доступ к таблице email'у сервисного аккаунта (**Редактор**)

### 3. Создайте бота у BotFather

1. Напишите [@BotFather](https://t.me/BotFather)
2. /newbot → получите токен
3. (опционально) Настройте команды: `start` — Запустить бота

### 4. Настройте переменные окружения

```bash
cp .env.example .env
```

Заполните `.env`:

```env
BOT_TOKEN=1234567890:AAF...
WEBHOOK_HOST=
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEET_ID=1abc...
APPLICATIONS_SHEET_NAME=Applications
OBJECTS_SHEET_NAME=Objects
ADMIN_IDS=1111111,2222222
```

### 5. Запустите

```bash
python main.py
```

Бот запустится в режиме **polling**.

---

## ☁️ Деплой на Railway

### 1. Подготовьте проект

Убедитесь, что в корне есть `Dockerfile`, `railway.json`, `requirements.txt`.

### 2. Загрузите на GitHub

```bash
git init
git add .
git commit -m "SmartRentBot initial"
```

### 3. Деплой

1. Зайдите на [Railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. Выберите репозиторий
4. Добавьте переменные в **Variables**:

| Variable | Значение |
|----------|----------|
| `BOT_TOKEN` | Токен от BotFather |
| `WEBHOOK_HOST` | `https://ваш-проект.up.railway.app` |
| `WEBHOOK_PATH` | `/webhook` |
| `PORT` | `8080` |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | `credentials.json` |
| `GOOGLE_SHEET_ID` | ID таблицы |
| `APPLICATIONS_SHEET_NAME` | `Applications` |
| `OBJECTS_SHEET_NAME` | `Objects` |
| `ADMIN_IDS` | ID админов через запятую |
| `PHOTOS_DIR` | `photos` |

5. **Важно:** загрузите `credentials.json` как файл в разделе **Files**

6. Деплой запустится автоматически. Railway сам выдаст HTTPS и установит webhook.

---

## 🏗 Структура проекта

```
smartrent_bot/
├── main.py                       # Точка входа (polling / webhook)
├── bot/
│   ├── __init__.py
│   ├── config.py                 # Переменные окружения
│   ├── states.py                 # FSM-состояния
│   ├── keyboards.py              # Все inline-клавиатуры
│   ├── google_sheets.py          # Google Sheets CRUD
│   ├── utils.py                  # Утилиты (скачивание фото)
│   ├── handlers.py               # Пользовательские обработчики + регистрация
│   └── handlers/
│       ├── __init__.py
│       ├── admin.py              # Админ-панель
│       └── objects.py            # CRUD объектов аренды
├── photos/
├── credentials.json              # (не добавлять в git)
├── Dockerfile
├── railway.json
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🧑‍💻 Роли

| Роль | Права |
|------|-------|
| **Пользователь** | Просмотр объектов, подача заявок, свои заявки и профиль |
| **Администратор** | Всё + админ-панель, управление объектами/заявками, рассылка |

---

## 📊 Статусы

### Заявки
| Ключ | Отображение |
|------|-------------|
| `new` | 🆕 Новый |
| `processing` | 🟡 В обработке |
| `confirmed` | 🟢 Подтверждён |
| `completed` | 🔵 Завершён |
| `cancelled` | 🔴 Отменён |

### Объекты
| Ключ | Отображение |
|------|-------------|
| `available` | 🟢 Доступен |
| `rented` | 🔴 Занят |
| `maintenance` | 🟡 На обслуживании |

---

## 🛠 Технологии

- **Python 3.11**
- **aiogram 2.25.1** — Telegram Bot API
- **Google Sheets API + gspread** — хранение данных
- **aiohttp** — webhook-сервер
- **Docker** — контейнеризация
- **Railway** — хостинг
