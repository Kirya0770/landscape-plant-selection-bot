# Landscape Plant Selection Bot

Telegram-бот для подбора растений под параметры участка: кислотность почвы, влажность, дренаж, освещенность и климатическую зону.

Проект автоматизирует поиск по каталогу декоративных культур (270+ записей), исключая ручной просмотр таблиц.

---

## Как устроен бот

* **База в оперативной памяти:** таблица `plants.xlsx` считывается один раз при старте сервиса через класс `PlantDatabase`. Бот не обращается к диску при запросах пользователей, сохраняя неблокирующую работу event loop.
* **Фильтрация:** отбор записей выполняется векторизованными масками библиотеки `pandas` по выбранным колонкам.
* **Пагинация:** список найденных культур выдается страницами по 5 карточек с кнопками навигации. Это предотвращает переполнение чата и блокировки по лимитам Telegram API.
* **Обновление на лету:** служебная команда `/reload` перечитывает Excel-файл без перезапуска самого бота на сервере.
* **Экранирование символов:** текст карточек рендерится в HTML через `html.escape`, что исключает падение парсера на спецсимволах в латинских наименованиях.

---

## Стек

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=flat-square)
![pandas](https://img.shields.io/badge/pandas-2.x-150458?style=flat-square)
![openpyxl](https://img.shields.io/badge/openpyxl-Excel_IO-green?style=flat-square)

---

## Установка и запуск

1. Склонируйте репозиторий:
   ```bash
   git clone [https://github.com/Kirya0770/landscape-plant-selection-bot.git](https://github.com/Kirya0770/landscape-plant-selection-bot.git)
   cd landscape-plant-selection-bot
