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
    "title": "sinoBot",
    "description": "Respond to mentions",
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
    "Uzi", "Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku", "c", 
    "korpm", "TTT", "Rudolf", "Jason", "huss", "Top", "Pars", "Zane", "Lisa", "$", 
    "Bri", "Devil", "Angel"]

staff_list = [
    "Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku", "Zane", "Lisa", "$", "Bri", "Devil", "Angel", "Ish"
]

# === Functions ===


def send_command(command):
    try:
        print(f"Sending command: {command}")
        ext.send_to_server(HPacket('Chat', command))
    except Exception as e:
        print(f"Error sending command '{command}': {e}")

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

ext.intercept(Direction.TO_CLIENT, on_speech, 'Chat')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Whisper')
ext.intercept(Direction.TO_SERVER, my_speech, 'Chat')
ext.intercept(Direction.TO_SERVER, my_speech, 'Whisper')
ext.intercept(Direction.TO_CLIENT, on_user_object, 'UserObject')

# === Start Anti-AFK Timer ===

print("Casino v2.1 Loaded Successfully!")