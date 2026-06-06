from aiogram import Dispatcher

from vpn_core.telegram_bot.handlers import admin, admin_catalog, menu, payments, purchase, services, support, wallet


def register_handlers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(menu.router)
    dispatcher.include_router(purchase.router)
    dispatcher.include_router(wallet.router)
    dispatcher.include_router(services.router)
    dispatcher.include_router(support.router)
    dispatcher.include_router(payments.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(admin_catalog.router)
