import asyncio
import html
import logging
import os
from pathlib import Path
from typing import Dict, List, Set

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
EXCEL_PATH = os.getenv("EXCEL_PATH", str(BASE_DIR / "plants.xlsx"))

if not BOT_TOKEN:
    raise ValueError("Критическая ошибка: переменная окружения BOT_TOKEN не найдена. Создайте файл .env.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CAT_MAP = {
    'Влажность': 'vl',
    'Дренаж': 'dr',
    'Климат': 'cl',
    'Свет': 'sw',
    'pH': 'ph'
}
REV_CAT_MAP = {v: k for k, v in CAT_MAP.items()}
PAGE_SIZE = 5


class PlantDatabase:
    """Кэширует датасет в памяти для быстрого неблокирующего доступа."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.df = pd.DataFrame()
        self.unique_options: Dict[str, List[str]] = {}
        self.load_data()

    def load_data(self) -> bool:
        if not os.path.exists(self.filepath):
            logging.error(f"Файл базы данных не найден по пути: {self.filepath}")
            return False
        try:
            df = pd.read_excel(self.filepath).fillna("")
            df.columns = [str(c).strip() for c in df.columns]
            self.df = df
            self._precompute_unique_values()
            logging.info(f"База растений успешно инициализирована: {len(self.df)} строк.")
            return True
        except Exception as e:
            logging.error(f"Ошибка при парсинге Excel: {e}")
            return False

    def _precompute_unique_values(self):
        self.unique_options.clear()
        for cat in CAT_MAP.keys():
            if cat not in self.df.columns:
                self.unique_options[cat] = []
                continue
            unique_items: Set[str] = set()
            for val in self.df[cat].astype(str):
                if not val or val.lower() == "nan":
                    continue
                if cat == 'Свет':
                    unique_items.add(val.strip())
                else:
                    parts = [p.strip() for p in val.replace(';', ',').split(',') if p.strip()]
                    unique_items.update(parts)
            self.unique_options[cat] = sorted(list(unique_items))


db = PlantDatabase(EXCEL_PATH)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

def get_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Параметры")],
            [KeyboardButton(text="📋 Мой выбор"), KeyboardButton(text="🔍 Найти")],
            [KeyboardButton(text="♻️ Очистить все")]
        ],
        resize_keyboard=True
    )


def get_categories_markup(data: dict) -> InlineKeyboardMarkup:
    buttons = []
    for cat in sorted(CAT_MAP.keys()):
        val = data.get(cat, [])
        display = ", ".join(val) if val else "—"
        buttons.append([InlineKeyboardButton(text=f"{cat}: {display}", callback_data=f"cat:{cat}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_options_markup(cat_full: str, selected: List[str]) -> InlineKeyboardMarkup:
    options = db.unique_options.get(cat_full, [])
    short_code = CAT_MAP.get(cat_full, "")
    buttons = []
    selected_set = {s.strip().lower() for s in selected}

    for idx, opt in enumerate(options):
        mark = "✅ " if opt.strip().lower() in selected_set else ""
        buttons.append([InlineKeyboardButton(text=f"{mark}{opt}", callback_data=f"idx:{short_code}:{idx}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_results_page_markup(matches: List[int], page: int) -> InlineKeyboardMarkup:
    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(matches))
    page_matches = matches[start_idx:end_idx]

    buttons = []
    for idx in page_matches:
        row = db.df.iloc[idx]
        name = str(row.get('Русское название', '—')).strip()
        buttons.append([InlineKeyboardButton(text=f"🌿 {name}", callback_data=f"info:{idx}:{page}")])

    nav_buttons = []
    total_pages = (len(matches) + PAGE_SIZE - 1) // PAGE_SIZE
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page:{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"page:{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)



@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data({c: [] for c in CAT_MAP.keys()})
    await message.answer(
        "🌿 <b>Бот готов к работе.</b>\nНастройте фильтры параметров для подбора растений.",
        reply_markup=get_main_kb()
    )


@dp.message(Command("reload"))
async def cmd_reload(message: types.Message):
    if db.load_data():
        await message.answer(f"✅ База данных успешно обновлена ({len(db.df)} строк).")
    else:
        await message.answer("❌ Ошибка чтения файла базы данных. Проверьте логи.")


@dp.message(F.text == "♻️ Очистить все")
async def cmd_clear(message: types.Message, state: FSMContext):
    await state.update_data({c: [] for c in CAT_MAP.keys()})
    await message.answer("♻️ Все фильтры сброшены.", reply_markup=get_main_kb())


@dp.message(F.text == "📋 Мой выбор")
async def cmd_my_choice(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected_items = [
        f"📍 <b>{html.escape(cat)}:</b> {html.escape(', '.join(data[cat]))}"
        for cat in sorted(CAT_MAP.keys()) if data.get(cat)
    ]
    if not selected_items:
        await message.answer("Вы еще не выбрали ни одного параметра.")
    else:
        await message.answer("<b>Ваш текущий выбор:</b>\n\n" + "\n".join(selected_items))


@dp.message(F.text == "⚙️ Параметры")
async def show_params(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        data = {c: [] for c in CAT_MAP.keys()}
        await state.set_data(data)
    await message.answer("Выберите категорию для настройки:", reply_markup=get_categories_markup(data))


@dp.message(F.text.contains("Найти"))
async def search_results(message: types.Message, state: FSMContext):
    data = await state.get_data()
    active_filters = {k: v for k, v in data.items() if v}

    if not active_filters:
        return await message.answer("⚠️ Выберите хотя бы один параметр в меню <b>⚙️ Параметры</b>!")
    if db.df.empty:
        return await message.answer("❌ База данных растений пуста или не загружена.")

    mask = pd.Series(True, index=db.df.index)
    for cat, vals in active_filters.items():
        if cat in db.df.columns:
            for v in vals:
                mask &= db.df[cat].astype(str).str.contains(v, case=False, na=False)

    matches = db.df[mask].index.tolist()
    await state.update_data(last_matches=matches)

    if not matches:
        await message.answer("❌ Подходящих растений не найдено. Попробуйте смягчить фильтры.")
    else:
        await message.answer(
            f"✅ Найдено растений: <b>{len(matches)}</b>\nВыберите позицию из списка:",
            reply_markup=get_results_page_markup(matches, page=0)
        )


@dp.callback_query(F.data.startswith("cat:"))
async def open_category(callback: types.CallbackQuery, state: FSMContext):
    cat_full = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get(cat_full, [])
    await callback.message.edit_text(
        f"📍 Выберите значение для <b>{html.escape(cat_full)}</b>:",
        reply_markup=get_options_markup(cat_full, selected)
    )


@dp.callback_query(F.data.startswith("idx:"))
async def handle_selection(callback: types.CallbackQuery, state: FSMContext):
    _, short_code, idx_str = callback.data.split(":")
    cat_full = REV_CAT_MAP.get(short_code, "")
    options = db.unique_options.get(cat_full, [])
    idx = int(idx_str)
    if idx >= len(options):
        return await callback.answer()

    chosen_val = options[idx].strip()
    data = await state.get_data()
    selected = data.get(cat_full, [])

    if cat_full == 'Климат':
        if chosen_val in selected:
            selected.remove(chosen_val)
        elif len(selected) < 2:
            selected.append(chosen_val)
        else:
            return await callback.answer("⚠️ Можно выбрать не более двух зон климата!", show_alert=True)
        await state.update_data({cat_full: selected})
        await callback.message.edit_reply_markup(reply_markup=get_options_markup(cat_full, selected))
    else:
        selected = [chosen_val]
        await state.update_data({cat_full: selected})
        await callback.message.edit_text("✅ Выбор зафиксирован:", reply_markup=get_categories_markup(await state.get_data()))
    await callback.answer()


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите параметры поиска:", reply_markup=get_categories_markup(await state.get_data()))


@dp.callback_query(F.data.startswith("page:"))
async def change_page(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    matches = data.get("last_matches", [])
    await callback.message.edit_reply_markup(reply_markup=get_results_page_markup(matches, page))
    await callback.answer()


@dp.callback_query(F.data.startswith("info:"))
async def show_full(callback: types.CallbackQuery):
    _, idx_str, page_str = callback.data.split(":")
    idx, page = int(idx_str), int(page_str)
    r = db.df.iloc[idx]

    care = str(r.get('Уход зимой/летом', '—')).replace(',', '\n').replace(';', '\n')
    care = care.replace("зимой:", "❄️ ЗИМОЙ:").replace("летом:", "☀️ ЛЕТОМ:")
    care_clean = "\n".join([line.strip() for line in care.split('\n') if line.strip()])

    name_ru = html.escape(str(r.get('Русское название', '')).upper())
    name_lat = html.escape(str(r.get('Официальное название', '')))
    description = html.escape(str(r.get('Описание', '—')))
    care_escaped = html.escape(care_clean)

    text = (
        f"🌿 <b>{name_ru}</b>\n"
        f"<i>({name_lat})</i>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 <b>ОПИСАНИЕ:</b>\n{description}\n\n"
        f"📋 <b>ИНСТРУКЦИЯ ПО УХОДУ:</b>\n{care_escaped}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ К списку вариантов", callback_data=f"page:{page}")
    ]])
    await callback.message.edit_text(text, reply_markup=kb)


@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен пользователем.")
