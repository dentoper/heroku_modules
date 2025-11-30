import asyncio
from datetime import datetime
from telethon import events, TelegramClient
from telethon.tl.types import UserStatusOnline, UserStatusOffline

# Конфигурация
BOT_USERNAME = "@your_bot_username"  # Замените на username вашего бота
AWAY_MESSAGE = "😴 Сейчас не в сети. Отвечу вам как только смогу!"
NOTIFICATION_MESSAGE = "🤖 Кто-то хочет с вами связаться"

# Хранилище состояний (в production используйте БД)
away_users = set()
pending_notifications = {}

class AwayHandler:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.setup_handlers()
    
    def setup_handlers(self):
        # Обработчик изменения статуса
        @self.client.on(events.UserUpdate())
        async def on_user_update(event):
            if event.original_update.user_id == await self.client.get_peer_id('me'):
                await self.handle_status_change(event)
        
        # Обработчик входящих личных сообщений
        @self.client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def on_private_message(event):
            if not event.out:
                await self.handle_private_message(event)
        
        # Команда для ручного включения/выключения режима "не в сети"
        @self.client.on(events.NewMessage(pattern=r'\.away', outgoing=True))
        async def set_away_mode(event):
            user_id = event.sender_id
            if user_id in away_users:
                away_users.remove(user_id)
                await event.edit("✅ Режим 'Не в сети' выключен")
            else:
                away_users.add(user_id)
                await event.edit("⏸️ Режим 'Не в сети' включен")
    
    async def handle_status_change(self, event):
        me = await self.client.get_me()
        
        # Проверяем, изменился ли статус на "не в сети"
        if hasattr(event.original_update, 'status'):
            if isinstance(event.original_update.status, UserStatusOffline):
                # Пользователь стал оффлайн
                away_users.add(me.id)
                print(f"Пользователь {me.id} теперь не в сети")
            elif isinstance(event.original_update.status, UserStatusOnline):
                # Пользователь стал онлайн
                if me.id in away_users:
                    away_users.remove(me.id)
                    print(f"Пользователь {me.id} теперь онлайн")
    
    async def handle_private_message(self, event):
        me = await self.client.get_me()
        sender = await event.get_sender()
        
        # Если мы не в сети и это не наше собственное сообщение
        if me.id in away_users and not event.out:
            try:
                # Отправляем автоответ
                await event.respond(AWAY_MESSAGE)
                print(f"Отправлен автоответ пользователю {sender.username or sender.id}")
                
                # Отправляем уведомление в бота (если настроен)
                if BOT_USERNAME:
                    notification = f"🔔 Пользователь {sender.first_name}"
                    if sender.username:
                        notification += f" (@{sender.username})"
                    notification += f" хочет с вами связаться!\nID: {sender.id}"
                    
                    await self.client.send_message(BOT_USERNAME, notification)
                    print(f"Уведомление отправлено боту {BOT_USERNAME}")
                
            except Exception as e:
                print(f"Ошибка при отправке уведомлений: {e}")

# Функция для инициализации плагина
def setup(client):
    return AwayHandler(client)
