import sys
import re
import random
import time
import threading
import keyboard
from collections import deque
from g_python.gextension import Extension
from g_python.hmessage import Direction, HMessage
from g_python.htools import RoomFurni, RoomUsers
from g_python.hpacket import HPacket
from g_python.hparsers import HUserUpdate, HEntity

extension_info = {
    "title": "Furniture Loader",
    "description": "Loads floor furniture data.",
    "version": "1.0",
    "author": "Ishak"
}

argv = sys.argv
if len(argv) < 2:
    argv = ["-p", "9092"]

ext = Extension(extension_info, argv, silent=True)
ext.start()
ext.send_to_server(HPacket('InfoRetrieve'))

room_furni = RoomFurni(ext)
room_users = RoomUsers(ext)

my_name = None
my_id = None
my_index = None

current_room_id = None

action_queue = []
target_furni = {}

taxi_ids = [2, 20, 16, 19, 11, 9, 15, 12, 4, 5, 8, 24, 23, 3, 6, 10, 14, 26, 7, 28, 18, 27]
last_taxis = []

staff_list = [
    "Zodiak","Ish","Shark", "H", "Ghost", "Sankru", "Susan", "Jeff", "Osama", "Goku",  "Zane", "Lisa", "$", "Bri", "Devil", "Angel", "c"
]

non_walkable_furni = [3266, 3277, 8120, 4240, 3178, 3534, 2518, 9831, 200009, 3725, 3267, 4435, 8517, 4306, 4287, 3330, 11655, 11626, 8890, 4932, 11647, 3714, 3275, 8029] #4435 = black hole
spawn_type_ids = {500100, 500101, 500102, 500103, 500104, 500105, 500106, 500107, 500108, 500109, 200009, 200010, 14316, 200360} # 200360: Micropig
trash_type_ids = {500100, 500101, 500102, 500103, 500104, 500105, 500106, 500107, 500108, 500109}
desired_wall_type_ids = {}
filtered_furni_list = {}

def on_floor_furni_loaded(floor_furni):
    global filtered_furni_list

    if floor_furni:
        for furni in floor_furni:
            if furni.type_id in trash_type_ids:
                filtered_furni_list[furni.id] = {
                    'type_id': furni.type_id,
                    'x': furni.tile.x,
                    'y': furni.tile.y
                }
            if furni.type_id in spawn_type_ids:
                ext.send_to_client(HPacket('ObjectAdd', furni.id, furni.type_id, furni.tile.x, furni.tile.y, 0, "0", "", 1, 0, "", -1, 0, 0, "Unknown User"))

room_furni.on_floor_furni_load(on_floor_furni_loaded)

#room_furni.request() # use at own risk

def select_closest_furni():
    global target_furni

    if check_staff():
        return

    if not target_furni:
        if filtered_furni_list:
            user_x, user_y = room_users.room_users[my_id].tile.x, room_users.room_users[my_id].tile.y
            closest_furni_id = None
            closest_distance = float('inf')

            for furni_id, furni_data in filtered_furni_list.items():
                furni_x, furni_y = furni_data['x'], furni_data['y']
                distance = ((furni_x - user_x) ** 2 + (furni_y - user_y) ** 2) ** 0.5

                if distance <= 1:
                    closest_furni_id = furni_id
                    closest_distance = distance
                    queue_action(closest_furni_id)
                    break

                if distance < closest_distance:
                    closest_distance = distance
                    closest_furni_id = furni_id

            if closest_furni_id is not None:
                closest_furni = filtered_furni_list[closest_furni_id]
                current_target_distance = float('inf')

                if target_furni:
                    target_x, target_y = list(target_furni.values())[0]['x'], list(target_furni.values())[0]['y']
                    current_target_distance = ((target_x - user_x) ** 2 + (target_y - user_y) ** 2) ** 0.5

                if closest_distance < current_target_distance:
                    target_furni = {closest_furni_id: closest_furni}
                    del filtered_furni_list[closest_furni_id]
                    start_walk()
        else:
            if len(room_users.room_users) == 1:
                taxi = get_random_taxi()
                message = f":taxi {taxi}"
                ext.send_to_server(HPacket('Chat', message, 0))
            else:
                ext.send_to_server(HPacket('StartTyping'))
                threading.Timer(1.5, send_taxi_message).start()

def check_staff():
    for user in room_users.room_users.values():
        if user.name in staff_list:
            print(f"Staff member found: {user.name}. Paused.")
            return True
    print("No staff members found in the room.")
    return False

def send_taxi_message():

    if check_staff():
        return

    taxi = get_random_taxi()
    message = f":taxi {taxi}"
    if not target_furni:
        ext.send_to_server(HPacket('Chat', message, 0))
        ext.send_to_server(HPacket('CancelTyping'))
    else:
        ext.send_to_server(HPacket('CancelTyping'))

def get_random_taxi():
    global last_taxis, current_room_id
    valid_taxi_ids = [taxi for taxi in taxi_ids if taxi not in last_taxis and taxi != current_room_id]
    
    if not valid_taxi_ids:
        raise ValueError("No more unique taxi IDs available!")
    
    random_taxi = random.choice(valid_taxi_ids)
    
    last_taxis.append(random_taxi)
    if len(last_taxis) > 5:
        last_taxis.pop(0)
    
    return random_taxi
    
def queue_action(furni_id):
    if furni_id not in action_queue:
        action_queue.append(furni_id)
        if len(action_queue) == 1:
            use_furni()

def on_object_remove(msg: HMessage):
    idk, furni_id = msg.packet.read('is')

    furni_id = int(furni_id)

    if furni_id in filtered_furni_list:
        del filtered_furni_list[furni_id]

    if furni_id in target_furni:
        print(f"Furni ID {furni_id} was removed. It matches the target furni.")
        action_queue.clear()
        del target_furni[furni_id]
        print("Target furni removed and action queue cleared.")

        select_closest_furni()


def on_object_add(msg: HMessage):
    id, type_id, x, y = msg.packet.read('iiii')

    if type_id in trash_type_ids:
        filtered_furni_list[id] = {
            'type_id': type_id,
            'x': x,
            'y': y
        }
    
        select_closest_furni()

def use_furni():
    if action_queue:
        furni_id = action_queue.pop(0)
        if furni_id in target_furni:
            furni = target_furni[furni_id]
            packet = HPacket('UseFurniture', furni_id, 0)
            packet = HPacket('UseFurniture', furni_id, 0)
            packet = HPacket('UseFurniture', furni_id, 0)
            ext.send_to_server(packet)
            if action_queue:
                use_furni()
    else:
        pass
    
def on_add_users(msg: HMessage):
    global my_index
    for user in room_users.room_users.values():
        if user.name == my_name:
            my_index = user.index
            break

def start_walk():
    room_constraints = {
        28: [(1, 11, 12, 24)],
        18: [(1, 24, 10, 18), (1, 7, 10, 24)],
        27: [(15, 24, 12, 24)],
        12: [(1, 8, 16, 24), (9, 22, 6, 24), (16, 22, 1, 5)],
        26: [(11, 24, 1, 24)],
        22: [
            (16, 22, 23, 24), (16, 24, 18, 24), 
            (13, 24, 16, 17), (13, 22, 11, 15), (13, 19, 1, 10)
        ]
    }

    if target_furni:
        furni_id, furni = next(iter(target_furni.items()))
        target_x, target_y = furni['x'], furni['y']

        if target_x != -1 and target_y != -1:
            relative_positions = [
                (-1, -1), (0, -1), (1, -1),
                (-1, 0), (0, 0), (1, 0),
                (-1, 1), (0, 1), (1, 1)
            ]

            constraints = room_constraints.get(current_room_id, None)

            for dx, dy in relative_positions:
                new_x, new_y = target_x + dx, target_y + dy

                if not (1 <= new_x <= 24 and 1 <= new_y <= 24):
                    continue

                if constraints and not any(
                    x_min <= new_x <= x_max and y_min <= new_y <= y_max
                    for x_min, x_max, y_min, y_max in constraints
                ):
                    continue

                furni_on_tile = [
                    furni for furni in room_furni.floor_furni
                    if furni.tile.x == new_x and furni.tile.y == new_y
                ]

                if any(furni.type_id in non_walkable_furni for furni in furni_on_tile):
                    continue

                is_free = True
                for other_user in room_users.room_users.values():
                    if (other_user.tile.x, other_user.tile.y) == (new_x, new_y):
                        is_free = False
                        break

                if is_free:
                    equation_x, equation_y = generate_equations(new_x, new_y)
                    ext.send_to_server(HPacket('MoveAvatar', equation_x, equation_y))
                    return

            threading.Timer(2, continuous_queue).start()



def on_user_update(msg: HMessage):
    updates = HUserUpdate.parse(msg.packet)

    room_constraints = {
        28: [(1, 11, 12, 24)],
        18: [(1, 24, 10, 18), (1, 7, 10, 24)],
        27: [(15, 24, 12, 24)],
        12: [(1, 8, 16, 24), (9, 22, 6, 24), (16, 22, 1, 5)],
        26: [(11, 24, 1, 24)],
        22: [
            (16, 22, 23, 24), (16, 24, 18, 24), 
            (13, 24, 16, 17), (13, 22, 11, 15), (13, 19, 1, 10)
        ]
    }

    for user in updates:
        matching_user = room_users.room_users.get(user.index)

        if matching_user:
            if user.index == my_index and target_furni:
                furni_id, furni = next(iter(target_furni.items()), (None, None))

                if furni:
                    target_x, target_y = furni['x'], furni['y']
                    print(f"Target furni coordinates: ({target_x}, {target_y})")

                    if target_x == -1 or target_y == -1:
                        print(f"Invalid target coordinates: ({target_x}, {target_y}), cannot walk there.")
                        continue

                    surrounding_tiles = [
                        (target_x-1, target_y-1), (target_x, target_y-1), (target_x+1, target_y-1),
                        (target_x-1, target_y),   (target_x, target_y),   (target_x+1, target_y),
                        (target_x-1, target_y+1), (target_x, target_y+1), (target_x+1, target_y+1)
                    ]

                    if (user.nextTile.x, user.nextTile.y) in surrounding_tiles or (user.tile.x, user.tile.y) in surrounding_tiles:
                        print(f"User is within range of the target, sending Pick Up request.")

                        if furni_id:
                            queue_action(furni_id)
                            use_furni()
                        else:
                            print(f"Furni ID not found.")
                    else:
                        relative_positions = [
                            (-1, -1), (0, -1), (1, -1),
                            (-1, 0), (0, 0), (1, 0),
                            (-1, 1), (0, 1), (1, 1)
                        ]
                        random.shuffle(relative_positions)

                        constraints = room_constraints.get(current_room_id, None)

                        for dx, dy in relative_positions:
                            new_x, new_y = target_x + dx, target_y + dy

                            if not (1 <= new_x <= 24 and 1 <= new_y <= 24):
                                continue

                            if constraints and not any(
                                x_min <= new_x <= x_max and y_min <= new_y <= y_max
                                for x_min, x_max, y_min, y_max in constraints
                            ):
                                print(f"Tile ({new_x}, {new_y}) is outside allowed ranges, skipping.")
                                continue

                            is_free = True

                            for other_user in room_users.room_users.values():
                                if (other_user.tile.x, other_user.tile.y) == (new_x, new_y):
                                    is_free = False
                                    print(f"Tile ({new_x}, {new_y}) is occupied by another user.")
                                    break

                            if is_free:
                                furni_on_tile = [
                                    furni for furni in room_furni.floor_furni
                                    if furni.tile.x == new_x and furni.tile.y == new_y
                                ]

                                if furni_on_tile:
                                    if any(furni.type_id in non_walkable_furni for furni in furni_on_tile):
                                        print(f"Tile ({new_x}, {new_y}) has non-walkable furniture, skipping.")
                                        continue
                                else:
                                    print(f"No furniture at tile ({new_x}, {new_y}).")

                                equation_x, equation_y = generate_equations(new_x, new_y)
                                ext.send_to_server(HPacket('MoveAvatar', equation_x, equation_y))
                                return

                            print(f"Tile ({new_x}, {new_y}) is occupied or invalid, skipping.")

def on_load_objects(msg: HMessage):
    msg.is_blocked = True

def on_open_connection(msg: HMessage):
    filtered_furni_list.clear()
    target_furni.clear()

def on_you_are_not_controller(msg: HMessage):
    ext.send_to_server(HPacket('Chat', ":rid", 0))

def on_recv_whisper(msg: HMessage):
    global current_room_id
    id, message, idk, bubbleType = msg.packet.read('isii')

    match = re.search(r'RoomID: (\d+)', message)
    if match:
        current_room_id = int(match.group(1))

        print("selecting random furni")

        select_closest_furni()

    if "Sorry, this work furniture is not enabled!" in message and target_furni:
        target_furni.clear()
        select_closest_furni()

    if "Sorry, we cannot taxi you out of this room!" in message:
        my_x = room_users.room_users[my_id].tile.x
        my_y = room_users.room_users[my_id].tile.y

        closest_furni = None
        closest_distance = float('inf')

        for furni in room_furni.floor_furni:
            furni_x = furni.tile.x
            furni_y = furni.tile.y

            if furni_x == my_x and furni_y == my_y:
                continue

            if furni.type_id != 200009:
                continue

            distance = ((furni_x - my_x) ** 2 + (furni_y - my_y) ** 2) ** 0.5

            if distance < closest_distance:
                closest_furni = furni
                closest_distance = distance

        if closest_furni:
            equation_x, equation_y = generate_equations(closest_furni.tile.x, closest_furni.tile.y)
            ext.send_to_server(HPacket('MoveAvatar', equation_x, equation_y))

def on_recv_shout(msg: HMessage):
    id, message = msg.packet.read('is')

    if "swings" in message and f"{my_name}" in message:
        filtered_furni_list.clear()
        target_furni.clear()
        taxi = get_random_taxi()
        message = f":taxi {taxi}"
        ext.send_to_server(HPacket('Chat', message, 0))

def on_user_object(msg: HMessage):
    global my_name, my_id
    (id, name) = msg.packet.read('is')
    my_id = id
    my_name = name

def anti_afk():
    ext.send_to_server(HPacket('AvatarExpression', 9))
    threading.Timer(30, anti_afk).start()
anti_afk()

def continuous_queue():
    if check_staff():
        return
    
    if target_furni:
        furni_id, _ = next(iter(target_furni.items()), (None, None))
        if furni_id and furni_id not in action_queue:
            queue_action(furni_id)
            print(f"Queued furni ID {furni_id}.")
        else:
            print("Target furni already in queue or no valid furni ID.")
    else:
        print("No target furni to queue.")
    threading.Timer(2, continuous_queue).start()

continuous_queue()

def hash_input(input_value):
    hash_output = (67 * input_value) % 10007
    hash_output = 271 + (137 ^ hash_output)
    return hex(hash_output)[2:].upper()

def to_equation(input_value):
    import random
    rand_val = random.random()
    if rand_val > 0.5:
        half_input = input_value // 2
        input_sub_half = input_value - half_input
        return f"{hash_input(half_input)} + {hash_input(input_sub_half)}"
    else:
        half_input = input_value + int(10 * random.random())
        input_sub_half = half_input - input_value
        return f"{hash_input(half_input)} - {hash_input(input_sub_half)}"

def generate_equations(x, y):
    encoded_x = to_equation(x)
    encoded_y = to_equation(y)
    return encoded_x, encoded_y

ext.intercept(Direction.TO_CLIENT, on_user_object, 'UserObject')
ext.intercept(Direction.TO_CLIENT, on_recv_whisper, 'Whisper')
ext.intercept(Direction.TO_CLIENT, on_recv_shout, 'Shout')
ext.intercept(Direction.TO_CLIENT, on_you_are_not_controller, 'YouAreNotController')
ext.intercept(Direction.TO_CLIENT, on_load_objects, 'Objects')
ext.intercept(Direction.TO_CLIENT, on_user_update, 'UserUpdate')
ext.intercept(Direction.TO_CLIENT, on_add_users, 'Users')
ext.intercept(Direction.TO_CLIENT, on_open_connection, 'OpenConnection')
ext.intercept(Direction.TO_CLIENT, on_object_remove, 'ObjectRemove')
ext.intercept(Direction.TO_CLIENT, on_object_add, 'ObjectAdd')

# ext.stop()