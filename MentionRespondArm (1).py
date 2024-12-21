import sys
import threading
import time
import random

from g_python.gextension import Extension
from g_python.hmessage import Direction, HMessage
from g_python.hpacket import HPacket
from g_python.htools import RoomUsers, HEntity

extension_info = {
    "title": "@ Respond",
    "description": "Respond to mentions Bobba",
    "version": "1.1",
    "author": "Ishak"
}

argv = sys.argv
if len(argv) < 2:
    argv = ["-p", 9092]

ext = Extension(extension_info, argv, silent=True)
ext.start()
ext.send_to_server(HPacket('InfoRetrieve'))

user = None
index = None
respond_enabled = True
last_message_time = 0

messages_list = ["uwu", "hlo", "hii", "yeSS", "HIII", "Yess", "helloo", "hii", "hi", "hi", "hii", "hello", "uwu", "Yes", "HII!", "hi!!!!!!!!!!"]

username_list = ["uzi","Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Alex", 
                 "Gosan", "paws", "R", "enemy", "Anne", "Annie", "Toni", 
                 "Ballin", "simple", "psycho", "BB-Ryda"]

room_users = RoomUsers(ext)

def send_message_after_delay(message, bubbleType, delay):
    def delayed_send():
        ext.send_to_server(HPacket('Chat', message, 0))
    timer = threading.Timer(delay, delayed_send)
    timer.start()

def on_retrieve(msg: HMessage):
    global user, index
    (idx, username) = msg.packet.read('is') # i = int, s = string, u = short, b = boolean, l = long
    user = username
    index = idx

def on_speech(msg: HMessage):
    global respond_enabled, last_message_time, room_users  # Access the global variables
    (idx, message) = msg.packet.read('is')
    
    user2: HEntity = room_users.room_users[idx]
    
    try:
        if ";startwork" in message.lower():
                    ext.send_to_server(HPacket('Chat', ":startwork", 0))

        if respond_enabled:
            if user2.name in username_list:
            # Send a packet to the server regardless of the cooldown
                

                if f"@{user}".lower() in message.lower():
                    current_time = time.time()
                
                    if current_time - last_message_time >= 20:
                        print("Sending messages with delays...")
                        random_message = random.choice(messages_list)
                        send_message_after_delay(random_message, 0, 4)  # Delay of 6 seconds
                    
                        last_message_time = current_time
                    else:
                        print(f"Cooldown active for messages. Time left: {20 - (current_time - last_message_time):.2f} seconds")
        else:
            print("Responding is disabled.")
            
    except Exception as e:
        print(f"Error occurred: {e}")
    
def my_speech(msg: HMessage):
    global respond_enabled
    (message, bubbleType) = msg.packet.read('si')

    if message.lower() == "//":
        msg.is_blocked = True
        respond_enabled = True
        ext.send_to_server(HPacket('Whisper', f"{user} Response to mentions is now ON.", 0))
    elif message.lower() == "dd":
        msg.is_blocked = True
        respond_enabled = False
        ext.send_to_server(HPacket('Whisper', f"{user} Response to mentions is now OFF.", 0))
    else:
        return
    
def anti_afk():
    ext.send_to_server(HPacket('AvatarExpression', 9))
    threading.Timer(30, anti_afk).start()  # Set the timer to repeat every 30 seconds

# Start the anti_afk function initially
anti_afk()

ext.intercept(Direction.TO_CLIENT, on_speech, 'Shout')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Chat')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Whisper')

ext.intercept(Direction.TO_SERVER, my_speech, 'Shout')
ext.intercept(Direction.TO_SERVER, my_speech, 'Chat')
ext.intercept(Direction.TO_SERVER, my_speech, 'Whisper')

ext.intercept(Direction.TO_CLIENT, on_retrieve, 'UserObject')