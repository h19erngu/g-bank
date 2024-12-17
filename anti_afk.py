import sys
import threading
from g_python.gextension import Extension
from g_python.hpacket import HPacket
from g_python.hmessage import Direction, HMessage

# === Extension Metadata ===
extension_info = {
    "title": "AntiAFK",
    "description": "Prevents auto-disconnection by sending periodic activity",
    "version": "1.0",
    "author": "Anonymous"
}

# === Global Configuration ===
argv = sys.argv
if len(argv) < 2:
    argv = ["-p", "9092"]

ext = Extension(extension_info, argv, silent=True)
ext.start()

# === Functions ===
def anti_afk():
    try:
        ext.send_to_server(HPacket('AvatarExpression', 9))  # Expression ID 9 (random activity)
        threading.Timer(60, anti_afk).start()  # Repeat every 60 seconds
        print("Anti-AFK pulse sent.")
    except Exception as e:
        print(f"Error in anti_afk: {e}")

def on_load_items(msg: HMessage):
    ext.send_to_server(HPacket('Chat', ":rid", 0))

# === Start Anti-AFK Timer ===
anti_afk()
ext.intercept(Direction.TO_CLIENT, on_load_items, 'Items')

print("AntiAFK v1.0 Loaded Successfully!")