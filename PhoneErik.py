import sys
import threading
import time
import random
import re

from g_python.gextension import Extension
from g_python.hmessage import Direction, HMessage
from g_python.hpacket import HPacket
from g_python.htools import RoomUsers, HEntity

# === Extension Metadata ===
extension_info = {
    "title": "PhoneBot",
    "description": "Respond to mentions and offer phones",
    "version": "2.0",
    "author": "Anon"
}

# === Global Configuration ===
argv = sys.argv
if len(argv) < 2:
    argv = ["-p", 9092]

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
    "Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku",  "Zane", "Lisa", "$", "Bri", "Devil", "Angel", "Ish"]

def process_coin_command(user, message):
    try:
        print(f"Processing command from user: {user.name}, message: {message}")

        if user.name == MY_NAME:
            print(f"Skipping processing for own command: {user.name}")
            return
        
        if check_staff():
            print(f"Staff member detected in room. Skipping command for: {user.name}")
            return

        if re.search(r'\b(offers|declines|gives)\b', message.lower()):
            print(f"Message contains 'offers', 'declines', or 'gives'. Skipping command for: {user.name}")
            return

        if re.search(r'\b(phone)\b', message.lower()):
            print(f"Detected 'phone' in message. Offering phone to: {user.name}")

            def delayed_process():
                try:
                    command = f":offer {user.name} phone"
                    ext.send_to_server(HPacket('Chat', command))
                    print(f"Sent phone offer to: {user.name}")
                except Exception as e:
                    print(f"Error offering phone to {user.name}: {e}")

            timer = threading.Timer(3.0, delayed_process)
            timer.start()
            return

        number_match = re.search(r'\b(\d+)\b', message)
        keyword_match = re.search(r'\b(credits|creds|texts|text message|messages)\b', message.lower())

        if number_match:
            amount = int(number_match.group(1))
            print(f"Detected number in message: {amount}")
            if amount > 49:
                print(f"Offering {amount} credits to: {user.name}")

                def delayed_process():
                    try:
                        command = f":offer {user.name} credits {amount}"
                        ext.send_to_server(HPacket('Chat', command))
                        print(f"Sent credit offer of {amount} to: {user.name}")
                    except Exception as e:
                        print(f"Error offering {amount} credits to {user.name}: {e}")

                timer = threading.Timer(3.0, delayed_process)
                timer.start()
        elif keyword_match:
            print(f"Detected keyword for default credit offer in message from: {user.name}")
            def delayed_process():
                try:
                    command = f":offer {user.name} credits 50"
                    ext.send_to_server(HPacket('Chat', command))
                    print(f"Sent default credit offer of 50 to: {user.name}")
                except Exception as e:
                    print(f"Error offering default credits to {user.name}: {e}")

            timer = threading.Timer(3.0, delayed_process)
            timer.start()
    except Exception as e:
        print(f"Error processing command from {user.name}: {e}")

# === Helper Functions ===
def check_staff():
    for user in room_users.room_users.values():
        if user.name in staff_list:
            print(f"Staff member found: {user.name}")
            return True
    print("No staff members found in the room.")
    return False


def send_message_after_delay(message, bubbleType, delay):
    def delayed_send():
        ext.send_to_server(HPacket('Chat', message, 0))
        ext.write_to_console(f"Sent delayed message: {message}")
    timer = threading.Timer(delay, delayed_send)
    timer.start()

def anti_afk():
    ext.send_to_server(HPacket('AvatarExpression', 9))
    threading.Timer(25, anti_afk).start()

def offer_phone(user):
    try:
        if not user or not hasattr(user, 'name'):
            ext.write_to_console(f"Invalid user object passed to offer_phone: {user}")
            return
        if user.name == MY_NAME or user.name in username_list or user.name in offered_users:
            return
        if not respond_enabled:
            return

        send_message_after_delay(f":offer {user.name} phone", 0, 8)
        offered_users.add(user.name)
        ext.write_to_console(f"Offered_users >> ${offered_users}")
    except Exception as e:
        ext.write_to_console(f"Error in offer_phone for {user.name if hasattr(user, 'name') else 'Unknown'}: {e}")

def handle_new_users(users):
    try:    
        if len(users) != 1:
            return

        user = users[0]
        ext.write_to_console(f"new user {user}")
        if hasattr(user, 'name'):
            offer_phone(user)
        else:
            ext.write_to_console(f"New user object does not have a 'name' attribute: {user}")
        
    except Exception as e:
        ext.write_to_console(f"Error handling new user {user.name if user else 'Unknown'}: {e}")

# === Event Handlers ===

def on_user_object(msg: HMessage):
    global MY_NAME, MY_ID
    id, name = msg.packet.read('is')
    MY_ID = id
    MY_NAME = name

def on_speech(msg: HMessage):
    global respond_enabled, last_message_time
    try:
        (idx, message) = msg.packet.read('is')
        user = room_users.room_users.get(idx)

        if not user or user.name == MY_NAME:
            return
        if not respond_enabled:
            return

        process_coin_command(user, message)

        if user.name in username_list and f"@{MY_NAME}".lower() in message.lower():
            current_time = time.time()
            if current_time - last_message_time >= 20:
                random_message = random.choice(messages_list)
                send_message_after_delay(random_message, 0, 4)
                last_message_time = current_time
            else:
                cooldown = 20 - (current_time - last_message_time)
                ext.write_to_console(f"Cooldown active for responding to mentions. Time left: {cooldown:.2f} seconds.")
    except Exception as e:
        ext.write_to_console(f"Error in on_speech: {e}")

def my_speech(msg: HMessage):
    global respond_enabled
    (message, bubbleType) = msg.packet.read('si')

    if message.lower() == "//":
        msg.is_blocked = True
        respond_enabled = True
        ext.write_to_console("Response to mentions is now ON.")
    elif message.lower() == "dd":
        msg.is_blocked = True
        respond_enabled = False
        ext.write_to_console("Response to mentions is now OFF.")

# === Event Bindings ===

room_users.on_new_users(handle_new_users)

ext.intercept(Direction.TO_CLIENT, on_speech, 'Shout')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Chat')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Whisper')

ext.intercept(Direction.TO_SERVER, my_speech, 'Shout')
ext.intercept(Direction.TO_SERVER, my_speech, 'Chat')
ext.intercept(Direction.TO_SERVER, my_speech, 'Whisper')

ext.intercept(Direction.TO_CLIENT, on_user_object, 'UserObject')

# === Start Anti-AFK Timer ===
anti_afk()
