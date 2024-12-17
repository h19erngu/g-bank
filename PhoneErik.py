import sys
import threading
import time
import random
import re

from g_python.gextension import Extension
from g_python.hmessage import Direction, HMessage
from g_python.hpacket import HPacket
from g_python.htools import RoomUsers

# === Extension Metadata ===
extension_info = {
    "title": "PhoneBot",
    "description": "Respond to mentions and offer phones",
    "version": "2.1",
    "author": "Anon"
}

# === Global Configuration ===
argv = sys.argv
if len(argv) < 2:
    argv = ["-p", "9092"]

ext = Extension(extension_info, argv, silent=True)
ext.start()
ext.send_to_server(HPacket('InfoRetrieve'))

# === Global Variables ===
MY_NAME = None
MY_ID = None
respond_enabled = True
last_message_time = 0
offered_users = set()
room_users = RoomUsers(ext)

messages_list = [
    "yo", ":D", "here", "yep", "sup", "im here", "hm", "yo boss", "right here", "yup",
    "yh", "mm", ":ok_hand:", "uwu", "yh", "yoo", "yh"
]

username_list = [
    "Demon", "Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku", "c", "harms", "chloee", "Hailey",
    "Nathan", "Mira", "Joseph", "Zane", "Lisa", "$", "Bri", "Devil", "Angel",
]

staff_list = [
    "Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku", "Zane", "Lisa", "$", "Bri", "Devil", "Angel", "Ish"
]

# === Functions ===

def process_coin_command(user, message):
    try:
        print(f"Processing command from {user.name}: {message}")

        if user.name == MY_NAME or user.name in staff_list:
            print("Skipping own command or staff member.")
            return

        if re.search(r'\b(phone)\b', message.lower()):
            print(f"Detected 'phone' in message. Offering phone to: {user.name}")
            threading.Timer(3.0, lambda: send_command(f":offer {user.name} phone")).start()
            return

        number_match = re.search(r'\b(\d+)\b', message)
        if number_match:
            amount = int(number_match.group(1))
            print(f"Detected credits number: {amount}")
            if amount > 49:
                threading.Timer(3.0, lambda: send_command(f":offer {user.name} credits {amount * 2}")).start()
                threading.Timer(4.0, lambda: send_command(f":offer {user.name} credits {amount}")).start()
        elif re.search(r'\b(credits|creds|texts|messages)\b', message.lower()):
            print(f"Detected keyword. Offering default credits to: {user.name}")
            threading.Timer(3.0, lambda: send_command(f":offer {user.name} credits 50")).start()
    except Exception as e:
        print(f"Error in process_coin_command: {e}")

def send_command(command):
    try:
        print(f"Sending command: {command}")
        ext.send_to_server(HPacket('Chat', command))
    except Exception as e:
        print(f"Error sending command '{command}': {e}")

def check_staff():
    for user in room_users.room_users.values():
        if user.name in staff_list:
            print(f"Staff detected in room: {user.name}")
            return True
    return False

def anti_afk():
    try:
        ext.send_to_server(HPacket('AvatarExpression', 9))
        threading.Timer(60, anti_afk).start()
    except Exception as e:
        print(f"Error in anti_afk: {e}")

def handle_new_users(users):
    for user in users:
        print(f"New user detected: {user.name}")
        if user.name not in offered_users:
            threading.Timer(5.0, lambda: send_command(f":offer {user.name} phone")).start()
            offered_users.add(user.name)

def on_user_object(msg: HMessage):
    global MY_NAME, MY_ID
    id, name = msg.packet.read('is')
    MY_ID = id
    MY_NAME = name
    print(f"Bot initialized. Name: {MY_NAME}, ID: {MY_ID}")

def on_speech(msg: HMessage):
    global last_message_time
    try:
        idx, message = msg.packet.read('is')
        user = room_users.room_users.get(idx)

        if not user or user.name == MY_NAME or not respond_enabled:
            return

        process_coin_command(user, message)

        if f"@{MY_NAME}".lower() in message.lower() and user.name in username_list:
            if time.time() - last_message_time >= 20:
                threading.Timer(4.0, lambda: send_command(random.choice(messages_list))).start()
                last_message_time = time.time()
    except Exception as e:
        print(f"Error in on_speech: {e}")

def my_speech(msg: HMessage):
    global respond_enabled
    try:
        message, bubbleType = msg.packet.read('si')
        if message.lower() == "//":
            msg.is_blocked = True
            respond_enabled = True
            print("Bot responses: ENABLED.")
        elif message.lower() == "dd":
            msg.is_blocked = True
            respond_enabled = False
            print("Bot responses: DISABLED.")
    except Exception as e:
        print(f"Error in my_speech: {e}")

# === Event Bindings ===

room_users.on_new_users(handle_new_users)

ext.intercept(Direction.TO_CLIENT, on_speech, 'Chat')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Whisper')
ext.intercept(Direction.TO_SERVER, my_speech, 'Chat')
ext.intercept(Direction.TO_SERVER, my_speech, 'Whisper')
ext.intercept(Direction.TO_CLIENT, on_user_object, 'UserObject')

# === Start Anti-AFK Timer ===
anti_afk()

print("PhoneBot v2.1 Loaded Successfully!")