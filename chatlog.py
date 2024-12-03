import sys
import time
import requests
import discord
import random
from g_python.gextension import Extension
from g_python.hmessage import Direction, HMessage
from g_python.htools import RoomUsers, HEntity
from g_python.hpacket import HPacket
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_LOG_WEBHOOK_URL = os.getenv("DISCORD_LOG_WEBHOOK_URL")
DISCORD_SPAM_WEBHOOK_URL = os.getenv("DISCORD_SPAM_WEBHOOK_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
YOUR_DISCORD_USER_ID = os.getenv("YOUR_DISCORD_USER_ID")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

extension_info = {
    "title": "Chatlog",
    "description": "just ocd innit",
    "version": "1.1",
    "author": "Ishak"
}

ext = Extension(extension_info, sys.argv, silent=True)
users = RoomUsers(ext)
MY_NAME = None
MY_ID = None
IRL_NAME = "erik"

user_colors = {}


def get_random_color():
    return random.randint(0x000000, 0xFFFFFF)


def get_user_color(username):
    if username not in user_colors:
        user_colors[username] = get_random_color()
    return user_colors[username]


def handle_new_users(users):
    if len(users) != 1:
        return
    try:
        user = users[0]
        user_name = user.name if hasattr(user, 'name') else str(user)
        if user_name != MY_NAME:
            log_message = f"📥 [{user_name}] has entered the room."
            send_embed_to_discord(user_name, log_message, DISCORD_LOG_WEBHOOK_URL)
    except Exception as e:
        ext.write_to_console(f"Error handling new user {user_name}: {e}")


def on_user_remove(msg: HMessage):
    _, user_id = msg.packet.read('is')
    user_id = int(user_id)
    try:
        user = users.room_users[user_id]
        del users.room_users[user_id]
        if user.name != MY_NAME:
            log_message = f"🚪 {user.name} has left the room."
            send_embed_to_discord(user.name, log_message, DISCORD_LOG_WEBHOOK_URL)
    except KeyError:
        pass
    except Exception as e:
        print(f"An error occurred while handling user removal: {e}")


def send_to_discord(message, webhook_url):
    try:
        payload = {"content": message}
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Error sending message to Discord: {e}")


def send_embed_to_discord(username, message, webhook_url):
    try:
        embed = {
            "embeds": [
                {
                    "description": f"{username}: {message}",
                    "color": get_user_color(username)
                }
            ]
        }
        requests.post(webhook_url, json=embed)
    except Exception as e:
        print(f"Error sending embed to Discord: {e}")


def input_to_bobba(message):
    try:
        ext.send_to_server(HPacket('Chat', f"{message}", 0))
        ext.send_to_server(HPacket('CancelTyping'))
    except Exception as e:
        print(f"Error sending message to game: {e}")


def on_bobba_chat(msg: HMessage):
    try:
        id, message, idk, bubbleType = msg.packet.read('isii')
        user = users.room_users.get(id)
        if not user:
            return

        try:
            message = message.encode('latin1').decode('utf-8').strip()
        except UnicodeDecodeError:
            return

        forbidden_phrases = [
            "from their chequings account and places it in their pockets",
            "from their pocket and deposits it into their chequings account*",
            "receives their paycheck for completing their shift*",
            "has been taken off as you have started working!",
            "tries to use their",
            "swings their",
            "swings at",
            "pushes",
            "pulls",
            "grabs a pair of armor and puts it on*",
            "is logging out in 15 seconds!",
            "mjölnir",
            "angel blade",
            "sword",
            "takes off their armor*",
            "for selling",
            "begin working a new shift!",
            "your armor",
            "you are cooling down",
            "you cannot rob in this room!",
            "you cannot un-escort",
            "clickthrough mode is now:",
            "someone onto an arrow!",
            "is not close enough!"
        ]

        if any(phrase in message.lower() for phrase in forbidden_phrases):
            return

        if "you receieve your paycheck!" in message:
            send_embed_to_discord(user.name, message, DISCORD_SPAM_WEBHOOK_URL)
        elif " You receive a cut" in message:
            send_embed_to_discord(user.name, message, DISCORD_SPAM_WEBHOOK_URL)
        else:
            if "RoomID: 105" in message:
                input_to_bobba(":startwork")
                send_embed_to_discord("System", message, DISCORD_LOG_WEBHOOK_URL)
            elif MY_NAME and (MY_NAME.lower() in message or IRL_NAME.lower() in message.lower()):
                send_to_discord(f"<@{YOUR_DISCORD_USER_ID}>", DISCORD_LOG_WEBHOOK_URL)
                send_embed_to_discord(user.name, message, DISCORD_LOG_WEBHOOK_URL)
            else:
                send_embed_to_discord(user.name, message, DISCORD_LOG_WEBHOOK_URL)
    except Exception as e:
        print(f"Error in on_bobba_chat: {e}")


def on_user_object(msg: HMessage):
    global MY_NAME, MY_ID
    (id, name) = msg.packet.read('is')
    MY_ID = id
    MY_NAME = name


def on_load_items(msg: HMessage):
    ext.send_to_server(HPacket('Chat', ":rid", 0))


@client.event
async def on_ready():
    send_embed_to_discord("SYSTEM", f'Logged in as {client.user}', DISCORD_SPAM_WEBHOOK_URL)
    send_embed_to_discord("SYSTEM", f'Logged in as {client.user}', DISCORD_LOG_WEBHOOK_URL)


@client.event
async def on_message(message):
    if message.author == client.user or message.webhook_id:
        return
    if message.channel.id == DISCORD_CHANNEL_ID:
        if message.content:
            input_to_bobba(message.content)


@client.event
async def on_typing(channel, user, when):
    if channel.id == DISCORD_CHANNEL_ID:
        ext.send_to_server(HPacket('StartTyping'))


async def start_discord_bot():
    await client.start(BOT_TOKEN)


users.on_new_users(handle_new_users)

ext.intercept(Direction.TO_CLIENT, on_user_remove, 'UserRemove')
ext.intercept(Direction.TO_CLIENT, on_bobba_chat, 'Chat')
ext.intercept(Direction.TO_CLIENT, on_bobba_chat, 'Whisper')
ext.intercept(Direction.TO_CLIENT, on_bobba_chat, 'Shout')
ext.intercept(Direction.TO_CLIENT, on_user_object, 'UserObject')
ext.intercept(Direction.TO_CLIENT, on_load_items, 'Items')

if __name__ == "__main__":
    ext.start()
    ext.send_to_server(HPacket('InfoRetrieve'))
    asyncio.run(start_discord_bot())
