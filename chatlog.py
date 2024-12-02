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

extension_info = {
    "title": "Chatlog",
    "description": "just ocd innit",
    "version": "1.1",
    "author": "Ishak"
}

DISCORD_LOG_WEBHOOK_URL = "https://discord.com/api/webhooks/1312015995954663424/toLnD8xvaEX5TI737DfsYDVj7ipvSmiMnp-O3MpdFO_tc8UNJ6BJ1Pcv-YUgaIczYHNs"
DISCORD_SPAM_WEBHOOK_URL = "https://discord.com/api/webhooks/1312178620646821958/dVb5r-YVV36CZcZXf5K2yf1NjzScouwIfgNeMCfTKojAhP3dhXxoUpWWuzMG0qOo6Ntu"
BOT_TOKEN = "MTMxMTg0ODExMjMyNjcwOTI4OA.GT9Qoc.jA2DAalQfxOYK1QpqUS_TVkWi0lZSGEvXL69p0"
DISCORD_CHANNEL_ID = 1311864221293613066
YOUR_DISCORD_USER_ID = "254761709015793665"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

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
        log_message = f"📥 [{user_name}] has entered the room."
        send_embed_to_discord(user_name, log_message, DISCORD_LOG_WEBHOOK_URL)
        print(f"New user: {user_name}")
    except Exception as e:
        ext.write_to_console(f"Error handling new user {user_name}: {e}")
        print(f"Error handling new user {user_name}: {e}")

def on_user_remove(msg: HMessage):
    _, user_id = msg.packet.read('is')
    user_id = int(user_id)

    try:
        print("Handling removed user with ID:", user_id)
        user: HEntity = users.room_users[user_id]
        del users.room_users[user_id]

        log_message = f"🚪 {user.name} has left the room."
        send_embed_to_discord(user.name, log_message, DISCORD_LOG_WEBHOOK_URL)

        print(f"User {user.name} with ID {user_id} removed.")
    except KeyError:
        print(f"User with ID {user_id} not found in room_users.")
    except Exception as e:
        print(f"An error occurred while handling user removal: {e}")


def send_to_discord(message, webhook_url):
    try:
        message = message.encode('utf-8').decode('utf-8')
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print(f"Message sent to Discord: {message}")
        elif response.status_code == 429:  # Rate limited
            print(f"Rate limited.")

        else:
            print(f"Failed to send message to Discord. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending message to Discord: {e}")

def send_embed_to_discord(username, message, webhook_url):
    try:
        embed = {
            "embeds": [
                {
                    "description": username + ": " + message,
                    "color": get_user_color(username)
                }
            ]
        }
        response = requests.post(webhook_url, json=embed)

        if response.status_code == 204:
            print(f"Embed sent to Discord: {message}")
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            print(f"Rate limited. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            send_embed_to_discord(username, message, webhook_url)
        else:
            print(f"Failed to send embed to Discord. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending embed to Discord: {e}")

def input_to_bobba(message):
    try:
        message = message.encode('utf-8').decode('utf-8')
        ext.send_to_server(HPacket('Chat', f"{message}", 0))
        ext.send_to_server(HPacket('CancelTyping'))
    except Exception as e:
        print(f"Error sending message to game: {e}")

def on_bobba_chat(msg: HMessage):
    try:
        (id, message) = msg.packet.read('is')
        user = users.room_users.get(id)
        if not user:
            return

        message = message.encode('latin1').decode('utf-8').strip().lower()

        if any(phrase in message.lower() for phrase in ["swings at", "pulls", "pushes"]):
            return
        if "you receieve your paycheck!" in message:
            send_embed_to_discord(user.name, message, DISCORD_SPAM_WEBHOOK_URL)
        elif "their paycheck for completing their shift*" in message:
            send_embed_to_discord(user.name, message, DISCORD_SPAM_WEBHOOK_URL)
        elif "remaining till you receive" in message:
            send_embed_to_discord(user.name, message, DISCORD_SPAM_WEBHOOK_URL)
        elif " You receive a cut" in message:
            send_embed_to_discord(user.name, message, DISCORD_SPAM_WEBHOOK_URL)
        else:
            if "you are currently in roomid:" in message:
                send_embed_to_discord("System", message, DISCORD_LOG_WEBHOOK_URL)
            elif MY_NAME and (MY_NAME.lower() in message or IRL_NAME.lower() in message.lower()):  # Case-insensitive comparison
                send_to_discord(f"<@{YOUR_DISCORD_USER_ID}>@everyone", DISCORD_LOG_WEBHOOK_URL)
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
    ext.send_to_server(HPacket('Chat', ":startwork", 0))

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    for guild in client.guilds:
        for channel in guild.text_channels:
            print(f"Channel ID: {channel.id}, Name: {channel.name}")
            if channel.id == DISCORD_CHANNEL_ID:
                print(f"[DEBUG] Bot is watching typing in channel: {channel.name}")

    send_embed_to_discord("SYSTEM", f'Logged in as {client.user}', DISCORD_SPAM_WEBHOOK_URL)
    send_embed_to_discord("SYSTEM", f'Logged in as {client.user}', DISCORD_LOG_WEBHOOK_URL)


@client.event
async def on_message(message):
    # Log the author's name and ID
    print(f"Author: {message.author} (ID: {message.author.id})")

    # Check if the message is from the bot
    if message.author == client.user:
        return

    # Check if the message is from a webhook
    if message.webhook_id:
        return

    # Check if the message is in the specified channel
    print(f"Channel: {message.channel} (ID: {message.channel.id})")
    if message.channel.id != DISCORD_CHANNEL_ID:
        print(f"{message.channel.id} - Message is not in the designated channel (Expected: {DISCORD_CHANNEL_ID}). Ignoring.")
        return
    
    # Log the content of the message
    if message.content:
        print(f"Message content: {message.content}")

        # Forward Discord messages to the game
        input_to_bobba(message.content)
        print("Message forwarded to the game.")
    else:
        print("Message has no content.")


@client.event
async def on_typing(channel, user, when):
    # Check if the typing event is in the channel you want
    if channel.id == DISCORD_CHANNEL_ID:  # Only track typing in the desired channel
        print(f"{user} is typing message in {channel.name} at {when}")
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
