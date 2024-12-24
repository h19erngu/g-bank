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
    "title": "BankBot",
    "description": "Respond to mentions and offer bank accounts",
    "version": "2.0",
    "author": "Ishak"
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
offered_users = set(['april', 'menny', 'Mouse', 'Dani', 'voyvitu', 'Precious', '-DVRSTx', 'huss', 
                     'Milla', 'korpm', 'PapiPanda', 'Mason', 'nad', 'Niall', 'BossAndCEO', 'electrica', 
                     'goated', 'Jonkonia', 'k2', 'Subwuf', 'ffs', 'flacko', 'bef', 'fairy', 'Lek', 'alibabes', 
                     'BillHicks', 'DRILLA', 'Plus', '1', 'Ray', 'kio', 'Berkhan', 'ketamine', '3490934902', 'wtf', 
                     'Cock', 'rakel', 'Heidi', 'tamago', 'agony', 'meow', 'Bio', 'Nasty', 'PepGuardiola', 'Montreal', 
                     'Elnor', 'T', 'Trust', '3490934903', 'Virgil', 'Iivid', 'Motion', 'OP', '2', 'Secret', 'sweetener', 
                     'Titan', 'OD', 'muba', 'sf', 'File', 'DiddysBabyOil', 'Top', 'ed', 'ackerman', 'nik', 'babi', 
                     'conreppin', 'Pars', 'Pizza', 'BBTF', 'IQ', 'ramazan', 'afk', 'cheese', 'Sett', 'Wei', 'asco', 
                     'miryoker', 'Mizeria', 'Mo', 'Supernatural', 'Morwan', 'Joseph', 'LloydsBank', 'night', 'melancholy', 
                     'cool', 'seventeen', 'Reece', 'paquito', 'Shanni', 'pugly', 'chip', 'Baro', 'gdluck', 'Appiah', 'P', 
                     'Whiplash', 'abdi', 'm4a1l9i7k', 'dyst', 'Scrapper', 'sicko', 'NigerianFarmer', 'j', '6', 'magnus', 
                     'des', 'Pineapple', 'Luz', 'bug', 'Kastro', 'dizzy', 'cookinwitkya', 'sol', 'mala', 'Allbehind', 
                     'Acacia', 'mig', 'Chase-Chris', 'Low', '69', 'harv', 'Bad', 'ink', 'ric', 'slapper', 'yan', 'Loud', 
                     'Smack', 'V', 'Doll', 'YG', 'Acnologia', 'Guts', 'nelura', 'Hentai', 'Flight', 'purplemash', 'Aishido', 
                     'W22', 'Roboxy', 'Yak', 'sadlegendguy947', 'Armz', 'hayl', 'Sour', 'furkan', 'Nitro', 'sav', 'hayley', 'G', 
                     'DoctorWho', 'Nuts', 'Total', 'violently', 'Scorp', 'NotStun', 'myth', 'bobs', 'Ish', 'Fullmetal', 'giulia', 
                     'Enes', 'Stundawg', 'mad', 'rush', 'OG', '10', 'chico', 'xp', 'Murder',
                      'L', 'Y', 'Leesa', 'Mommy', 'Kritz', 'TooFast', 'High', 'rd', 'Shark', 'Awasy', 'Jason'])

'april', 'menny', 'Mouse', 'Dani', 'voyvitu', 'Precious', '-DVRSTx', 'huss', 'Milla', 'korpm', 'PapiPanda', 'Mason', 'nad', 'Niall', 'BossAndCEO', 'electrica', 'goated', 'Jonkonia', 'k2', 'Subwuf', 'ffs', 'flacko', 'bef', 'fairy', 'Lek', 'alibabes', 'BillHicks', 'DRILLA', 'Plus', '1', 'Ray', 'kio', 'Berkhan', 'ketamine', '3490934902', 'wtf', 'Cock', 'rakel', 'Heidi', 'tamago', 'agony', 'meow', 'Bio', 'Nasty', 'PepGuardiola', 'Montreal', 'Elnor', 'T', 'Trust', '3490934903', 'Virgil', 'Iivid', 'Motion', 'OP', '2', 'Secret', 'sweetener', 'Titan', 'OD', 'muba', 'sf', 'File', 'DiddysBabyOil', 'Top', 'ed', 'ackerman', 'nik', 'babi', 'conreppin', 'Pars', 'Pizza', 'BBTF', 'IQ', 'ramazan', 'afk', 'cheese', 'Sett', 'Wei', 'asco', 'miryoker', 'Mizeria', 'Mo', 'Supernatural', 'Morwan', 'Joseph', 'LloydsBank', 'night', 'melancholy', 'cool', 'seventeen', 'Reece', 'paquito', 'Shanni', 'pugly', 'chip', 'Baro', 'gdluck', 'Appiah', 'P', 'Whiplash', 'abdi', 'm4a1l9i7k', 'dyst', 'Scrapper', 'sicko', 'NigerianFarmer', 'j', '6', 'magnus', 'des', 'Pineapple', 'Luz', 'bug', 'Kastro', 'dizzy', 'cookinwitkya', 'sol', 'mala', 'Allbehind', 'Acacia', 'mig', 'Chase-Chris', 'Low', '69', 'harv', 'Bad', 'ink', 'ric', 'slapper', 'yan', 'Loud', 'Smack', 'V', 'Doll', 'YG', 'Acnologia', 'Guts', 'nelura', 'Hentai', 'Flight', 'purplemash', 'Aishido', 'W22', 'Roboxy', 'Yak', 'sadlegendguy947', 'Armz', 'hayl', 'Sour', 'furkan', 'Nitro', 'sav', 'hayley', 'G', 'DoctorWho', 'Nuts', 'Total', 'violently', 'Scorp', 'NotStun', 'myth', 'bobs', 'Ish', 'Fullmetal', 'giulia', 'Enes', 'Stundawg', 'mad', 'rush', 'OG', '10', 'chico', 'xp', 'Murder', 'L', 'Y', 'Leesa', 'Mommy', 'Kritz', 'TooFast', 'High', 'rd', 'Shark', 'Awasy', 'Jason'
room_users = RoomUsers(ext)

messages_list = [
    "yo", ":D", "here", "yep", "sup", "im here", "hm", "yo boss", "right here", "yup", 
    "yh", "mm", ":ok_hand:", "uwu", "yh", "yoo", "yh"
]

username_list = [
    "Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku", "ed", "Ballin","sav" , "simple", "psycho", "BB-Ryda", "Zane", "Lisa", "$", "Bri", "Devil", "Angel",
]

staff_list = [
    "Zodiak", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku",  "Zane", "Lisa", "$", "Bri", "Devil", "Angel", "c"
]

# === Helper Functions ===
def check_staff():
    for user in room_users.room_users.values():
        if user.name in staff_list:
            print(f"Staff member found: {user.name}")
            return True
    print("No staff members found in the room.")
    return False

def send_message_after_delay(message, bubbleType, delay):
    """Send a message to the server after a specified delay."""
    def delayed_send():
        ext.send_to_server(HPacket('Chat', message, 0))
        ext.write_to_console(f"Sent delayed message: {message}")
    timer = threading.Timer(delay, delayed_send)
    timer.start()

def anti_afk():
    """Send periodic actions to prevent being marked as AFK."""
    ext.send_to_server(HPacket('AvatarExpression', 9))
    threading.Timer(25, anti_afk).start()

def offer_bankaccount(user):
    """Offer a bank account to a user if not already offered."""
    try:
        if not user or not hasattr(user, 'name'):
            ext.write_to_console(f"Invalid user object passed to offer_bankaccount: {user}")
            return
        
        if user.name == MY_NAME or user.name in username_list or user.name in offered_users:
            return
        
        if not respond_enabled:
            return

        send_message_after_delay(f":offer {user.name} bankaccount", 0, 8)
        offered_users.add(user.name)
        ext.write_to_console(f"Offered_users >> ${offered_users}")
    except Exception as e:
        ext.write_to_console(f"Error in offer_bankaccount for {user.name if hasattr(user, 'name') else 'Unknown'}: {e}")

def process_coin_command(user, message):
    """Process coin-related commands (withdraw, deposit)."""
    try:
        if user.name == MY_NAME:
            return
        
        
        if check_staff():
            return

        # if "Bulb" in [u.name for u in room_users.room_users.values()]:
        #     return

        # Match valid commands
        relaxed_match = re.search(r'\b(?:withdraw|deposit|dep)\b.*?(\d+)\b', message.lower())
        strict_match = re.match(r'^with\s+(\d+)$', message.lower().strip())

        if relaxed_match:
            amount = relaxed_match.group(1)
            command_type = "withdraw" if "withdraw" in message.lower() else "deposit"
        elif strict_match:
            amount = strict_match.group(1)
            command_type = "withdraw"
        else:
            return

        def delayed_process():
            try:
                command = f":{command_type} {user.name} {amount}"
                ext.send_to_server(HPacket('Chat', command))
                ext.write_to_console(f"Processed {command_type} for {user.name} with amount {amount}.")
            except Exception as e:
                ext.write_to_console(f"Error in delayed_process for {command_type} command by {user.name}: {e}")

        timer = threading.Timer(3.0, delayed_process)
        timer.start()

        ext.write_to_console(f"Detected {command_type} command for {user.name}: '{message}' -> Amount: {amount}")
    except Exception as e:
        ext.write_to_console(f"Error in process_coin_command for {user.name}: {e}")

def handle_new_users(users):
    try:    
        if len(users) != 1:
            return

        user = users[0]
        ext.write_to_console(f"-new user {user}")
        if hasattr(user, 'name'):
            offer_bankaccount(user)
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
    """Handle chat messages."""
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
    """Intercept and process user's outgoing messages."""
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

def on_user_remove(msg: HMessage):
    _, user_id = msg.packet.read('is')
    user_id = int(user_id)
    try:
        if user_id in room_users.room_users:
            user = room_users.room_users[user_id]
            del room_users.room_users[user_id]

    except KeyError:
        pass
    except Exception as e:
        print(f"Error handling user removal: {e}")
# === Event Bindings ===

room_users.on_new_users(handle_new_users)

ext.intercept(Direction.TO_CLIENT, on_user_remove, 'UserRemove')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Shout')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Chat')
ext.intercept(Direction.TO_CLIENT, on_speech, 'Whisper')
ext.intercept(Direction.TO_SERVER, my_speech, 'Shout')
ext.intercept(Direction.TO_SERVER, my_speech, 'Chat')
ext.intercept(Direction.TO_SERVER, my_speech, 'Whisper')
ext.intercept(Direction.TO_CLIENT, on_user_object, 'UserObject')

# === Start Anti-AFK Timer ===
anti_afk()