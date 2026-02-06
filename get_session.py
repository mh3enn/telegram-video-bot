from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 35198332
API_HASH = "236ab0a7906c073f9f891c70670c7d39"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\nSESSION_STRING:\n")
    print(client.session.save())
