import logging
import os
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import gspread  # pip install gspread oauth2client
from google.oauth2.service_account import Credentials

# ────────────────────────────────────────────────────────────────────────────────
# Configuration ─ replace with your actual values or keep as env variables
# ────────────────────────────────────────────────────────────────────────────────
BOT_TOKEN = "7909750598:AAHThcMpi5Vz-obpiCl1Lv4mryQXPqCzSVs"  # Telegram bot token
GSHEET_ID = "1ohRzvfBFLlfXAOvvLqMP48Fa2hl30bO00JxydnVEXrU"  # ID of the Google Sheet (the long string in the URL)
SERVICE_ACCOUNT_JSON = { 'key': 1
} #path to service-account json or JSON string

print("DEBUG  BOT_TOKEN =", bool(BOT_TOKEN))
print("DEBUG  GSHEET_ID =", GSHEET_ID)
print("DEBUG  SERVICE_ACCOUNT_JSON =", SERVICE_ACCOUNT_JSON)


# List of shops and product groups (order matters!)
SHOPS = [
    "Магазин 1",
    "Магазин 2",
    "Магазин 3",
    "Магазин 4",
    "Магазин 5",
    "Магазин 6",
    "Магазин 7",
    "Магазин 8",
]

PRODUCT_GROUPS = [
    "Жижа",
    "Жижа план",
    "Элки",
    "Элки план",
    "Снюс",
    "Растафарай",
    "Жвачки и Шоколадки",
    "Напитки + пиво",
    "Сигареты",
    "Табак для кальяна + комплектующие",
    "Сигариллы / самокрутки",
]

RATING_LABELS = {
    5: "Отлично",
    4: "Хорошо",
    3: "Нормально",
    2: "Плохо",
    1: "Очень плохо",
}

# ────────────────────────────────────────────────────────────────────────────────
# Google Sheets helper
# ────────────────────────────────────────────────────────────────────────────────

def _get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if isinstance(SERVICE_ACCOUNT_JSON, dict):
        creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_JSON, scopes=scopes)
    else:
        raise RuntimeError("SERVICE_ACCOUNT_JSON must be dict in this version")
    return gspread.authorize(creds)

def save_to_sheet(row):
    _get_gsheet_client().open_by_key(GSHEET_ID).sheet1.append_row(row, value_input_option="USER_ENTERED")

# ────────────────────────────────────────────────────────────────────────────────
# FSM States
# ────────────────────────────────────────────────────────────────────────────────

class Form(StatesGroup):
    choosing_shop = State()
    entering_name = State()
    rating_group = State()  # holds index in PRODUCT_GROUPS via state data
    optional_comment = State()

# ────────────────────────────────────────────────────────────────────────────────
# Keyboard helpers
# ────────────────────────────────────────────────────────────────────────────────

def shop_kb():
    kb = InlineKeyboardBuilder()
    for s in SHOPS:
        kb.button(text=s, callback_data=s)
    kb.adjust(1)
    return kb

def rate_kb():
    kb = InlineKeyboardBuilder()
    for sc in range(5, 0, -1):
        kb.button(text=f"{sc} — {RATING_LABELS[sc]}", callback_data=str(sc))
    kb.button(text="⬅️ Назад", callback_data="BACK")
    kb.adjust(1)
    return kb

# ────────────────────────────────────────────────────────────────────────────────
# Bot setup
# ────────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
print(BOT_TOKEN)
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не установлена!")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ────────────────────────────────────────────────────────────────────────────────
# Handlers
# ────────────────────────────────────────────────────────────────────────────────

# ─── BOT ───────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ─── HANDLERS ──────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Привет! Выбери магазин:", reply_markup=shop_kb().as_markup())
    await state.set_state(Form.choosing_shop)

@dp.callback_query(Form.choosing_shop, F.data.in_(SHOPS))
async def choose_shop(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(shop=callback.data)
    await callback.message.edit_text("Введите ваше имя продавца:")
    await state.set_state(Form.entering_name)
    await callback.answer()

@dp.message(Form.entering_name, F.text.len() > 1)
async def got_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip(), ratings={}, idx=0)
    await message.answer(f"Оцените <b>{PRODUCT_GROUPS[0]}</b> (1–5):", reply_markup=rate_kb().as_markup())
    await state.set_state(Form.rating_group)

@dp.callback_query(Form.rating_group)
async def rating_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = data.get("idx", 0)
    ratings = data.get("ratings", {})

    if callback.data == "BACK":
        if idx == 0:
            await callback.answer("Вы уже на первой группе", show_alert=True)
            return
        idx -= 1
        await state.update_data(idx=idx)
        await callback.message.edit_text(f"Оцените <b>{PRODUCT_GROUPS[idx]}</b> (1–5):", reply_markup=rate_kb().as_markup())
        await callback.answer()
        return

    # оценка
    if callback.data.isdigit():
        ratings[PRODUCT_GROUPS[idx]] = int(callback.data)
        idx += 1
        await state.update_data(idx=idx, ratings=ratings)

        if idx < len(PRODUCT_GROUPS):
            await callback.message.edit_text(f"Оцените <b>{PRODUCT_GROUPS[idx]}</b> (1–5):", reply_markup=rate_kb().as_markup())
        else:
            await callback.message.edit_text("Введите комментарий (это обязательное поле)")
            await state.set_state(Form.optional_comment)
    await callback.answer()

@dp.message(Form.optional_comment)
async def finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text
    row = [datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"), data["shop"], data["name"]]
    row += [data["ratings"].get(g, "") for g in PRODUCT_GROUPS] + [comment]
    try:
        save_to_sheet(row)
        await message.answer("✅ Спасибо! Данные сохранены.")
    except Exception as e:
        logging.exception("Failed to save to Google Sheet")
        await message.answer(f"⚠️ Не удалось записать в таблицу: {e}")
    await state.clear()


# ────────────────────────────────────────────────────────────────────────────────
# Runner
# ────────────────────────────────────────────────────────────────────────────────

def main():
    import asyncio
    async def _run():
        await dp.start_polling(bot)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
