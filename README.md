# FS Device Spy

This project enables automatic discovery and management of Linux-based boards that regularly send broadcast messages using `bcsend_linux` on the local network. It provides a Python-based solution for receiving, managing, and connecting (SSH, RDP, SFTP) to these boards.

## Components

- **receiver_daemon.py**: Runs as a background service and collects all boards sending broadcasts. Information is stored in `boards.json`, and boards are automatically removed if they are no longer reachable.
- **ssh_connect.py**: Interactive tool to list boards and connect via SSH, RDP, or SFTP.
- **boards.json**: Automatically maintained list of all currently reachable boards.

## Requirements

- Python 3
- `xfreerdp` (for RDP connections)
- A file manager that supports `xdg-open` (for SFTP)
- Boards must use `bcsend_linux` and be in the same network

## Usage

### 1. Start the receiver daemon

```bash
python3 receiver_daemon.py
```

The daemon runs continuously and automatically updates `boards.json`.

### 2. List available boards

```bash
python3 ssh_connect.py --boards
```

### 3. Connect to a board

- **SSH:**

  ```bash
  python3 ssh_connect.py --ssh --board <index> --user <username>
  ```

  (Default user: root)

- **RDP:**

  ```bash
  python3 ssh_connect.py --rdp --board <index> --user <username>
  ```

- **SFTP (File Manager):**

  ```bash
  python3 ssh_connect.py --sftp --board <index> --user <username>
  ```

### Notes

- Boards remain in the list as long as they are reachable (ping test), even if they stop sending broadcasts.
- The board list is automatically updated and cleaned up.

## License

MIT License

---

**F&S Device Spy** – Automatic network discovery and convenient access to embedded Linux boards.
