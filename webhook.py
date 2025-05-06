"""
Запускает aiohttp-сервер, принимает апдейты от Telegram и
скармливает их вашему Dispatcher из main.py.
"""

import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from main import dp, BOT_TOKEN          # <-- импортируйте готовый dp

# env-переменные, которые зададим на Cloud Run
BASE_URL       = os.environ["BASE_URL"]          # https://<run-url>
WEBHOOK_PATH   = os.getenv("WEBHOOK_PATH", "/tg")    # любой endpoint
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
app = web.Application()

async def handle(request: web.Request):
    # простая проверка, что запрос именно от Telegram
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return web.Response(status=403)
    update = bot._parse_webhook_update(await request.json())
    await dp.feed_update(bot, update)
    return web.Response(text="ok")

app.router.add_post(WEBHOOK_PATH, handle)

async def on_startup(_: web.Application):
    await bot.set_webhook(f"{BASE_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET)

async def on_cleanup(_: web.Application):
    await bot.delete_webhook()

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
