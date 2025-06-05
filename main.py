import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import BotCommand

# Локальные импорты
from core.settings import settings
from core.database.db import get_users_enable, create_table_users
from core.utils.get_gas import get_gas
from core.handlers.basic import start, get_user_info, alert, filter_text
from core.handlers.open_profile import start_open_profile, get_id, get_url, yes_or_not_open
from core.handlers.create_profile import start_create_profile, get_count, get_proxies, get_app_id, yes_or_not_create
from core.utils.open_profile_state import OpenProfile
from core.utils.create_profile_state import CreateProfile


async def set_command(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать работу с ботом"),
        BotCommand(command="/get_user_info", description="Получить данные о пользователе"),
        BotCommand(command="/alert", description="Подписаться на рассылку"),
        BotCommand(command="/open_profile", description="Открыть профиль"),
        BotCommand(command="/create_profile", description="Создать профиль")
    ]
    await bot.set_my_commands(commands)


async def monitoring(bot: Bot):
    """Фоновая задача для мониторинга и оповещения пользователей"""
    monitoring_interval = 15

    while True:
        try:
            users_id = await get_users_enable()
            gas_now = await get_gas()

            for user_id in users_id:
                try:
                    await bot.send_message(user_id[0], text=f"Текущий газ: {gas_now}")
                except Exception as err:
                    logging.warning(f"Не удалось отправить сообщение пользователю {user_id[0]}: {err}")

            await asyncio.sleep(monitoring_interval)

        except Exception as err:
            logging.error(f"Ошибка в мониторинге: {err}", exc_info=True)
            await asyncio.sleep(60)  # Подождать перед повторной попыткой


async def main():
    # Инициализация базы данных
    await create_table_users()

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - "
               "(%(filename)s.%(funcName)s(%(lineno)d)) - %(message)s"
    )

    bot = Bot(settings.bots.bot_token)
    dp = Dispatcher()

    # Установка команд бота
    await set_command(bot)

    # Регистрация обработчиков команд
    dp.message.register(start, Command(commands="start"))
    dp.message.register(get_user_info, Command(commands="get_user_info"),
                        F.from_user.id.in_(settings.bots.admins_id))
    dp.message.register(alert, Command(commands="alert"))

    # Обработчики для работы с профилями
    dp.message.register(start_open_profile, Command(commands="open_profile"))
    dp.message.register(get_id, OpenProfile.get_id)
    dp.message.register(get_url, OpenProfile.get_url)
    dp.callback_query.register(yes_or_not_open, F.data.in_(['yes_open', 'no_open']))

    # Обработчики для создания профилей
    dp.message.register(start_create_profile, Command(commands="create_profile"))
    dp.message.register(get_count, CreateProfile.get_count)
    dp.message.register(get_app_id, CreateProfile.get_app_id)
    dp.message.register(get_proxies, CreateProfile.get_proxies)
    dp.callback_query.register(yes_or_not_create, F.data.in_(['yes_create', 'no_create']))

    # Обработчик текстовых сообщений
    dp.message.register(filter_text, F.text)

    # Запуск фоновых задач (раскомментировать при необходимости)
    # asyncio.create_task(monitoring(bot))

    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}", exc_info=True)

