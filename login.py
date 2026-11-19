from telethon import TelegramClient
import os

api_id = 12345678          # API_ID خودت
api_hash = "you_api_hash"  # API_HASH خودت

os.makedirs("sessions", exist_ok=True)

# اسم سشن رو دقیقا myacc1 بذار تا self.py پیداش کنه
client = TelegramClient("sessions/myacc1", api_id, api_hash)

async def main():
    await client.start()
    me = await client.get_me()
    print(f"✅ Logged in as: {me.first_name} | ID: {me.id}")
    await client.disconnect()

with client:
    client.loop.run_until_complete(main())
