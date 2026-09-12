# Landscape Plant Selection Bot

Telegram-бот для подбора растений под условия участка (тип почвы, освещенность, влажность, дренаж и климатическая зона). 

Проект разработан под прикладную задачу: ускорить ручной подбор по базе питомника из 270+ видов растений без обращения к таблицам вручную.

---

## Архитектура и особенности

* **Кэш базы в памяти:** файл `plants.xlsx` считывается один раз при запуске бота через класс `PlantDatabase`. Повторных чтений файла с диска при запросах пользователей нет, что исключает блокировку event loop.
* **Поиск без зависаний:** фильтрация вариантов выполняется через векторизованные маски `pandas`.
* **Постраничная выдача:** результаты разбиваются по 5 карточек на страницу с кнопками навигации («Назад / Вперед»), чтобы не перегружать чат и не упираться в лимиты Telegram API на спам сообщениями.
* **Обновление на лету:** команда `/reload` для администратора перечитывает Excel-файл без перезапуска сервиса на сервере.
* **Безопасная верстка:** сообщения формируются в HTML с экранированием (`html.escape`), что защищает парсер от падений из-за скобок и спецсимволов в ботанических названиях.

---

## Стек

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=flat-square)
![pandas](https://img.shields.io/badge/pandas-2.x-150458?style=flat-square)
![openpyxl](https://img.shields.io/badge/openpyxl-Excel_IO-green?style=flat-square)

---

## Локальный запуск

1. Склонируйте репозиторий:
   ```bash
   git clone [https://github.com/Kirya0770/landscape-plant-selection-bot.git](https://github.com/Kirya0770/landscape-plant-selection-bot.git)
   cd landscape-plant-selection-bot
