import socket
import struct
import json
import threading
import time
import sys
import os

BROADCAST_PORT = 4242
BUFFER_SIZE = 1024
BOARDS_FILE = "boards.json"
BOARD_TIMEOUT = 120  # seconds

BCASTINFOV2_FORMAT = '<64s64s64s3H2s16s'
BCASTINFOV2_SIZE = struct.calcsize(BCASTINFOV2_FORMAT)

def parse_bcastinfov2(data):
    if len(data) < BCASTINFOV2_SIZE:
        return None
    unpacked = struct.unpack(BCASTINFOV2_FORMAT, data[:BCASTINFOV2_SIZE])
    devname = unpacked[0].split(b'\0', 1)[0].decode(errors='ignore')
    devinfo = unpacked[1].split(b'\0', 1)[0].decode(errors='ignore')
    ident = unpacked[2].split(b'\0', 1)[0].decode(errors='ignore')
    wMAC = unpacked[3:6]
    mac_bytes = [wMAC[0] & 0xFF, (wMAC[0] >> 8) & 0xFF,
                 wMAC[1] & 0xFF, (wMAC[1] >> 8) & 0xFF,
                 wMAC[2] & 0xFF, (wMAC[2] >> 8) & 0xFF]
    mac_str = ':'.join(f'{b:02X}' for b in mac_bytes)
    ip_addr = unpacked[7].split(b'\0', 1)[0].decode(errors='ignore')
    return {
        "devname": devname,
        "devinfo": devinfo,
        "ident": ident,
        "mac": mac_str,
        "ip": ip_addr
    }

def save_boards(boards):
    tmp_file = BOARDS_FILE + ".tmp"
    with open(tmp_file, "w") as f:
        json.dump(boards, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(tmp_file, BOARDS_FILE)
    except FileNotFoundError:
        print(f"[receiver_daemon] Warning: Could not find {tmp_file} to replace {BOARDS_FILE} (may be a race condition).")

def load_boards():
    if os.path.exists(BOARDS_FILE):
        with open(BOARDS_FILE) as f:
            return json.load(f)
    return {}

def is_reachable(ip):
    response = os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1")
    return response == 0

def cleanup_boards(boards):
    now = time.time()
    cleaned = {}
    for k, v in boards.items():
        if now - v["last_seen"] < BOARD_TIMEOUT:
            cleaned[k] = v
        else:
            # Try to ping the board before removing
            ip = v.get("ip")
            if ip and is_reachable(ip):
                cleaned[k] = v  # Still reachable, keep it
    return cleaned

def receiver_loop(runtime=None):
    boards = load_boards()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", BROADCAST_PORT))
    print(f"[receiver_daemon] Listening for broadcast messages on UDP port {BROADCAST_PORT}...")
    start_time = time.time()
    try:
        while True:
            if runtime is not None and (time.time() - start_time) >= runtime:
                print(f"[receiver_daemon] Runtime of {runtime}s reached - exiting")
                break
            sock.settimeout(1.0)
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                continue
            sender_ip, _ = addr
            parsed = parse_bcastinfov2(data)
            if parsed:
                key = parsed["mac"]
                parsed["last_seen"] = time.time()
                parsed["sender_ip"] = sender_ip
                boards[key] = parsed
                boards = cleanup_boards(boards)
                save_boards(boards)
                print(f"[receiver_daemon] Updated: {parsed['ident']} ({parsed['ip']}) [{parsed['mac']}] from {sender_ip}")
    except KeyboardInterrupt:
        print("[receiver_daemon] Exiting...")
    finally:
        sock.close()

def cleanup_thread():
    while True:
        time.sleep(30)
        boards = load_boards()
        boards = cleanup_boards(boards)
        save_boards(boards)

def cleanup_boards_file_on_start():
    if not os.path.exists(BOARDS_FILE):
        return
    try:
        with open(BOARDS_FILE) as f:
            boards = json.load(f)
    except Exception:
        return
    changed = False
    to_delete = []
    for k, v in boards.items():
        ip = v.get("ip")
        if not ip or not is_reachable(ip):
            to_delete.append(k)
    for k in to_delete:
        print(f"[receiver_daemon] Removing unreachable board on startup: {boards[k].get('ident','?')} ({boards[k].get('ip','?')}) [{k}]")
        del boards[k]
        changed = True
    if changed:
        tmp_file = BOARDS_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(boards, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, BOARDS_FILE)

def main():
    cleanup_boards_file_on_start()
    runtime = None
    if len(sys.argv) > 1:
        try:
            runtime = int(sys.argv[1])
            print(f"[receiver_daemon] Running for max {runtime} seconds")
        except ValueError:
            print("[receiver_daemon] Invalid runtime argument, ignoring")
    t = threading.Thread(target=cleanup_thread, daemon=True)
    t.start()
    receiver_loop(runtime)

if __name__ == "__main__":
    main()
