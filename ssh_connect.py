import json
import os
import subprocess
import sys
import argparse

BOARDS_FILE = "boards.json"

def load_boards():
    if os.path.exists(BOARDS_FILE):
        with open(BOARDS_FILE) as f:
            return json.load(f)
    return {}

def print_boards(boards, board_idx=None):
    if not boards:
        print("No boards found.")
        return
    if board_idx == "ALL" or board_idx is None:
        sorted_boards = sorted(boards.values(), key=lambda b: b["ident"])
        print("Available boards:")
        for idx, b in enumerate(sorted_boards):
            print(f"[{idx}] {b['ident']} | {b['ip']} | {b['mac']} | {b['devinfo']}")
    else:
        board = select_board(boards, board_idx)
        print(f"[{board_idx}] {board['ident']} | {board['ip']} | {board['mac']} | {board['devinfo']}")

def select_board(boards, board_idx=None):
    sorted_boards = sorted(boards.values(), key=lambda b: b["ident"])
    if not sorted_boards:
        print("No boards found.")
        sys.exit(1)
    if board_idx is not None:
        try:
            idx = int(board_idx)
            if 0 <= idx < len(sorted_boards):
                return sorted_boards[idx]
            else:
                print("Invalid board index.")
                sys.exit(1)
        except Exception:
            print("Invalid board index.")
            sys.exit(1)
    # Interactive selection fallback
    print_boards(boards)
    sel = input("Select board number: ")
    try:
        sel = int(sel)
        if 0 <= sel < len(sorted_boards):
            return sorted_boards[sel]
    except Exception:
        pass
    print("Invalid selection.")
    sys.exit(1)

def is_reachable(ip):
    response = os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1")
    return response == 0

def main():
    parser = argparse.ArgumentParser(description="SSH, RDP, or SFTP connect to a board")
    parser.add_argument("--ssh", action="store_true", help="Connect via SSH")
    parser.add_argument("--rdp", action="store_true", help="Connect via RDP (xfreerdp)")
    parser.add_argument("--sftp", action="store_true", help="Open board via SFTP using xdg-open")
    parser.add_argument("--user", default="root", help="SSH/RDP/SFTP username (default: root)")
    parser.add_argument("--boards", nargs="?", const="ALL", help="List all available boards or a specific board by index")
    parser.add_argument("--board", type=int, help="Index of board to connect to (see --boards)")
    args = parser.parse_args()

    boards = load_boards()

    if args.boards:
        print_boards(boards, args.boards)
        sys.exit(0)

    if args.ssh or args.rdp or args.sftp:
        if args.board is None:
            print("You must specify --board <index> to connect.")
            print_boards(boards)
            sys.exit(1)
        board = select_board(boards, args.board)
        user = args.user or "root"
        ip = board["ip"]
        if not is_reachable(ip):
            print(f"Board {ip} is not reachable (ping failed). Aborting.")
            sys.exit(1)
        if args.ssh:
            print(f"Connecting to {user}@{ip} via SSH ...")
            subprocess.run(["ssh", f"{user}@{ip}"])
        elif args.rdp:
            print(f"Connecting to {user}@{ip} via RDP ...")
            subprocess.run(["ssh", f"{user}@{ip}", "fsremote.sh"])
            subprocess.run(["xfreerdp", f"/u:{user}", f"/v:{ip}"])
        elif args.sftp:
            sftp_url = f"sftp://{user}@{ip}/"
            print(f"Opening {sftp_url} via xdg-open ...")
            subprocess.run(["open", sftp_url])
        sys.exit(0)

    parser.print_help()
    sys.exit(1)

if __name__ == "__main__":
    main()
