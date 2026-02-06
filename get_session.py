from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 123456
API_HASH = "API_HASH_HERE"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\nSESSION_STRING:\n")
    print(client.session.save())
