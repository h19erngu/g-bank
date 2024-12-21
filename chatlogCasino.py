import sys
import time
import requests
import discord
import re
import threading
import os
from dotenv import load_dotenv
from threading import Lock
from queue import Queue
from g_python.gextension import Extension
from g_python.hmessage import Direction, HMessage
from g_python.htools import RoomUsers, HEntity
from g_python.hpacket import HPacket

extension_info = {
    "title": "chatlog",
    "description": "just ocd innit",
    "version": "1",
    "author": "Ishak"
}

ext = Extension(extension_info, sys.argv, silent=True)
ext.start()
ext.send_to_server(HPacket('InfoRetrieve'))

users = RoomUsers(ext)

my_personal_name = ["erik"] # add how many nicknames u want
staff_list = ["Uzi","Zodiak", "H", "Ghost", "sankru", "S", "Jeff", "Osama", "Goku", "c", "Lisa",
               "$", "Bri", "Devil", "Angel", "Zane", "Leesa",
               "Pars","Roboxy","huss","korpm","Top","Jason","Rudolf",
               "Annie","Anne","69","Toni","Gosan","R","Alex","paws"]
my_name = None
my_id = None

batch_size = 20  # Max number of messages in one batch
batch_delay = 60  # Seconds to wait before sending the batch

message_batch = []

load_dotenv()
DISCORD_LOG_WEBHOOK_URL = os.getenv('DISCORD_LOG_WEBHOOK_URL')
DISCORD_SPAM_WEBHOOK_URL = os.getenv('DISCORD_SPAM_WEBHOOK_URL')
TOKEN = os.getenv('TOKEN')
MY_DISCORD_ID = os.getenv('MY_DISCORD_ID')
ALLOWED_CHANNELS = int(os.getenv('ALLOWED_CHANNELS'))

intents = discord.Intents.all()
intents.message_content = True
intents.typing = True

client = discord.Client(intents=intents)

message_queue = Queue()

send_lock = threading.Lock()

processed_users = set()

def clear_processed_users():
    global processed_users
    processed_users.clear()
    #print("Processed users cleared.")

def handle_new_users(users):
    global my_name, processed_users

    if len(users) != 1:
        return
    
    try:
        user = users[0]
        user_name = user.name if hasattr(user, 'name') else str(user)

        if user_name not in processed_users:
            if user_name != my_name:
                log_message = f"📥 [{user_name}] has entered the room."
                queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x000000)
            processed_users.add(user_name)
            
            timer = threading.Timer(1.0, clear_processed_users)
            timer.start()
        #else:
            #print(f"User {user_name} is already processed, skipping.")
    
    except Exception as e:
        ext.write_to_console(f"Error handling new user {user_name}: {e}")
        print(f"Error handling new user {user_name}: {e}")

def on_user_remove(msg: HMessage):
    global my_name
    _, user_id = msg.packet.read('is')
    user_id = int(user_id)
    try:
        user: HEntity = users.room_users[user_id]
        del users.room_users[user_id]

        if user.name != my_name:
            log_message = f"🚪 {user.name} has left the room."
            queue_message(log_message, DISCORD_LOG_WEBHOOK_URL)
            #print(f"User {user.name} has left the room.")
        #else:
            #print(f"User {user.name} (same as my_name) left the room, not logging.")

    except KeyError:
        print(f"User with ID {user_id} not found in room_users.")
    except Exception as e:
        print(f"An error occurred while handling user removal: {e}")

users.on_new_users(handle_new_users)
ext.intercept(Direction.TO_CLIENT, on_user_remove, 'UserRemove')

def send_to_discord_embed(message, webhook_url, color=0x000000, mention_everyone=False):
    try:
        embed = {
            "content": "@everyone" if mention_everyone else "",
            "embeds": [
                {
                    "description": message,
                    "color": color
                }
            ]
        }

        response = requests.post(webhook_url, json=embed)
        if response.status_code == 429:  # Rate limited
            retry_after = int(response.headers.get("Retry-After", 0.5))
            print(f"Rate limited. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            return send_to_discord_embed(message, webhook_url, color, mention_everyone)
        elif response.status_code != 204:
            print(f"Failed to send message to Discord. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending embed to Discord: {e}")

def send_batch_to_discord(batch):
    try:
        combined_message = "\n".join([msg[0] for msg in batch])
        
        webhook_url = batch[0][1]
        color = batch[0][2]
        mention_everyone = batch[0][3]

        send_to_discord_embed(combined_message, webhook_url, color, mention_everyone)

        global last_sent_time
        last_sent_time = time.time()

    except Exception as e:
        print(f"Error sending message batch to Discord: {e}")

last_sent_time = 0
message_rate_limit = 1
rate_limit_lock = Lock()

def process_message_queue():
    global last_sent_time

    message_batch = []
    while True:
        if not message_queue.empty():
            message, webhook_url, color, mention_everyone = message_queue.get()

            message_batch.append((message, webhook_url, color, mention_everyone))

            if len(message_batch) >= batch_size:
                send_batch_to_discord(message_batch)
                message_batch.clear()

        if len(message_batch) > 0:
            current_time = time.time()
            if current_time - last_sent_time >= batch_delay:
                send_batch_to_discord(message_batch)
                message_batch.clear()

        time.sleep(0.1)

def queue_message(message, webhook_url, color=0x000000, mention_everyone=False):
    message_queue.put((message, webhook_url, color, mention_everyone))

queue_thread = threading.Thread(target=process_message_queue, daemon=True)
queue_thread.start()

def on_sent_whisper(msg: HMessage):
    message, bubbleType = msg.packet.read('si')
    message = message.encode('utf-8').decode('utf-8')
    match = re.match(r"(\S+) (.+)", message)
    if match:
        username = match.group(1)
        custom_message = match.group(2)

        log_message = f":speech_balloon:[WHISPER TO][{username}]: {custom_message}"
        queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFFD700)

def is_in_staff_list(username):
    return username in staff_list

def on_recv_chat(msg: HMessage):
    try:
        (id, message, idk, bubbleType) = msg.packet.read('isii')
        user = users.room_users.get(id)
        if not user:
            return

        message = message.encode('latin1').decode('utf-8')

        forbidden_terms = [
            "from their Chequings Account and places it in their pockets",
            "from their pocket and deposits it into their Chequings Account*",
            "receives their paycheck for completing their shift*",
            "tries to use their",
            "swings their",
            "swings at",
            "pushes",
            "pulls",
            "grabs a pair of Armor and puts it on*",
            "is logging out in 15 seconds!",
            "Mjölnir",
            "Angel Blade",
            "Sword",
            "takes off their Armor*",
            "and gives them a"
        ]
        
        if any(term.lower() in message.lower() for term in forbidden_terms):
            return

        if my_name and (
            (my_name.lower() in message.lower() or any(name.lower() in message.lower() for name in my_personal_name))
            and bubbleType not in [120, 118, 43] and "ishakk" not in message and "higher" not in message):
            log_message = f":index_pointing_at_the_viewer::skin-tone-3:[{user.name}]: {message}"
            queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFFD700)
            send_to_discord_embed(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFFD700, mention_everyone=True)

        elif is_in_staff_list(user.name):
            log_message = f":cop:[{user.name}]: {message}"
            # queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x808080)
            send_to_discord_embed(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x808080)

        elif id == my_id and message == "stops working as they have fallen asleep*":
            log_message = f":index_pointing_at_the_viewer::skin-tone-3:[{user.name}]: {message} YOU HAVE FALLEN ASLEEP"
            queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFFD700, mention_everyone=True)
            ext.send_to_server(HPacket('Chat', " ", 0))
            ext.send_to_server(HPacket('Chat', ":startwork", 0))

        elif id == my_id:
            log_message = f":star:[{user.name}]: {message}"
            queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFF0000)
            send_to_discord_embed(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFF0000)

        else:
            log_message = f":speech_balloon:[{user.name}]: {message}"
            queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x808080)

    except Exception as e:
        print(f"Error in on_recv_chat: {e}")

def on_recv_whisper(msg: HMessage):
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
            "your armor",
            "you are cooling down", 
            "you cannot rob in this room!",
            "you cannot un-escort",
            "clickthrough mode is now:",
            "someone onto an arrow!",
            "is not close enough!",
            "you have received $",
            "remaining till you receive your paycheck!",
            "5 event points!"
        ]
        if any(phrase in message.lower() for phrase in forbidden_phrases):
            return

        if "You are currently in RoomID:" in message:
            try:
                room_id = message.split("RoomID:")[1].strip(" !")
                log_message = f"Room ID Update\nYou are currently in RoomID: `{room_id}`"
                queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x1E90FF)
                if room_id == "107" or "105":
                    ext.send_to_server(HPacket('Chat', ":startwork", 0))
            except Exception as e:
                print(f"Error handling RoomID: {e}")
            return

        try:
            if bubbleType == 120:
                mention_message = re.sub(r'\[.*?\]', '', message).strip()
                log_message = f":skull:[GANG][{user.name}]: {mention_message}"
                queue_message(log_message, DISCORD_SPAM_WEBHOOK_URL, color=0x000000)

            elif bubbleType == 118 and "[VIP Alert]" in message:
                mention_message = message.replace("[VIP Alert]", "").strip()
                log_message = f":crown:[VIP] {mention_message}"
                queue_message(log_message, DISCORD_SPAM_WEBHOOK_URL, color=0xFFFF00)

            elif bubbleType == 43:
                mention_message = re.sub(r'\[.*?\]', '', message).strip()
                log_message = f":briefcase:[CORP][{user.name}]: {mention_message}"
                queue_message(log_message, DISCORD_SPAM_WEBHOOK_URL, color=0x964B00)

            elif bubbleType == 33:
                mention_message = re.sub(r'\[.*?\]', '', message).strip()
                log_message = f":tools:[STAFF] {mention_message}"
                queue_message(log_message, DISCORD_SPAM_WEBHOOK_URL, color=0xFFA500)

            elif id == my_id and bubbleType == 1:
                if "You begin working a new shift!" in message or \
                   "You have started your" in message:
                    log_message = f":briefcase:[CORP][{user.name}]: {message}"
                    queue_message(log_message, DISCORD_SPAM_WEBHOOK_URL, color=0x964B00)
                elif "you have earned" in message:
                    log_message = f":briefcase:[CORP] {message}"
                    queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x008000)
                elif "in your Bank Account." in message:
                    log_message = f":dollar:  {message}"
                    queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x008000)
                else:
                    log_message = f":information_source:[{user.name}]: {message}"
                    queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0x808080)

            elif id != my_id:
                mention_message = f"{message}"
                log_message = f":speech_balloon:[WHISPER FROM] [{user.name}]: {mention_message}"
                queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFFD700, mention_everyone=False)
        except Exception as e:
            print(f"Error handling bubble types: {e}")

    except Exception as e:
        print(f"Error in on_recv_whisper: {e}")

def send_message_to_game(message, sender_discord_id):
    global MY_DISCORD_ID
    try:
        message = message.encode('utf-8').decode('utf-8')

        if message.startswith(":whisper"):
            match = re.match(r":whisper (\S+) (.+)", message)
            if match:
                username = match.group(1)
                custom_message = match.group(2)

                ext.send_to_server(HPacket('Whisper', f"{username} {custom_message}", 0))
                ext.send_to_server(HPacket('CancelTyping'))

                log_message = f":speech_balloon:[WHISPER TO][{username}]: {custom_message}"
                queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFFD700)
            else:
                print("Invalid whisper format. Use :whisper <username> <message>")

        elif (message.startswith(":give") or message.startswith(":logout")) and str(sender_discord_id) != MY_DISCORD_ID:
            log_message = f"Lol nice try kiddo"
            queue_message(log_message, DISCORD_LOG_WEBHOOK_URL, color=0xFFD700, mention_everyone=True)

        else:
            ext.send_to_server(HPacket('Chat', f"{message}", 0))
            ext.send_to_server(HPacket('CancelTyping'))
    except Exception as e:
        print(f"Error sending message to game: {e}")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    for guild in client.guilds:
        for channel in guild.text_channels:
            print(f"Channel ID: {channel.id}, Name: {channel.name}")
            if channel.id == ALLOWED_CHANNELS:
                print(f"[DEBUG] Bot is watching typing in channel: {channel.name}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.webhook_id:
        return
    if message.channel.id != ALLOWED_CHANNELS:
        return

    if message.content:
        message_string = message.content.encode('utf-8').decode('utf-8')  
        send_message_to_game(message_string, message.author.id)
        # send_to_discord_embed(f"[Discord] {message.author}: {message_string}", DISCORD_LOG_WEBHOOK_URL, color=0x808080)

async def start_discord_bot():
    await client.start(TOKEN)

@client.event
async def on_typing(channel, user, when):
    if channel.id == ALLOWED_CHANNELS:
        print(f"{user} is typing message in {channel.name} at {when}")
        ext.send_to_server(HPacket('StartTyping'))

def on_user_object(msg: HMessage):
    global my_name, my_id
    (id, name) = msg.packet.read('is')
    my_id = id
    my_name = name

def on_load_items(msg: HMessage):
    ext.send_to_server(HPacket('Chat', ":rid", 0))

def anti_afk():
    ext.send_to_server(HPacket('AvatarExpression', 9))
    threading.Timer(45, anti_afk).start()

anti_afk()

ext.intercept(Direction.TO_CLIENT, on_recv_chat, 'Chat')
ext.intercept(Direction.TO_CLIENT, on_recv_chat, 'Shout')
ext.intercept(Direction.TO_CLIENT, on_recv_whisper, 'Whisper')
ext.intercept(Direction.TO_SERVER, on_sent_whisper, 'Whisper')
ext.intercept(Direction.TO_CLIENT, on_user_object, 'UserObject')
ext.intercept(Direction.TO_CLIENT, on_load_items, 'Items')

if __name__ == "__main__":
    import asyncio

    asyncio.run(start_discord_bot())