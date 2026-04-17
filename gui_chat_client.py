"""
gui_chat_client.py
------------------

Usage:
    python gui_chat_client.py
    python gui_chat_client.py -d <server_ip>
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import socket
import json
import argparse
import select

from chat_utils import mysend, myrecv, SERVER, CHAT_PORT, S_OFFLINE, S_LOGGEDIN, S_CHATTING
import client_state_machine as csm


class GUIClient:
    """
    Mirrors the logic of Client (chat_client_class.py) but drives
    everything through a Tkinter window instead of the terminal.

    Key differences from the original Client:
      - sm.proc(my_msg, peer_msg) returns a string  -> we display it
      - Login is handled in _do_login(), not a loop
      - Receiving runs in a background daemon thread
    """

    def __init__(self, root: tk.Tk, server_addr):
        self.root = root
        self.server_addr = server_addr

        self.socket = None
        self.sm = None
        self.name = ""
        self.running = False

        self.root.title("ICDS Chat")
        self.root.geometry("640x560")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self._build_login_screen()

    # ─── Login screen ────────────────────────────────────────────────────────

    def _build_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg="#1e1e2e")
        self.login_frame.pack(expand=True)

        tk.Label(
            self.login_frame, text="ICDS Chat",
            font=("Helvetica", 24, "bold"),
            bg="#1e1e2e", fg="#cdd6f4"
        ).pack(pady=(40, 6))

        tk.Label(
            self.login_frame, text="Enter your nickname",
            font=("Helvetica", 11),
            bg="#1e1e2e", fg="#6c7086"
        ).pack(pady=(0, 20))

        self.name_var = tk.StringVar()
        entry = tk.Entry(
            self.login_frame, textvariable=self.name_var,
            font=("Helvetica", 13), width=22,
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=6
        )
        entry.pack(pady=4)
        entry.focus()
        entry.bind("<Return>", lambda e: self._do_login())

        tk.Button(
            self.login_frame, text="Join",
            font=("Helvetica", 12, "bold"),
            bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec",
            relief="flat", bd=0, padx=20, pady=6,
            cursor="hand2",
            command=self._do_login
        ).pack(pady=12)

        self.login_status = tk.Label(
            self.login_frame, text="",
            font=("Helvetica", 10),
            bg="#1e1e2e", fg="#f38ba8"
        )
        self.login_status.pack()

    def _do_login(self):
        name = self.name_var.get().strip()
        if not name:
            self.login_status.config(text="Please enter a nickname.")
            return

        self.login_status.config(text="Connecting…", fg="#a6e3a1")
        self.root.update()

        # 1. Open socket — same as Client.init_chat()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(self.server_addr)
        except Exception as e:
            self.login_status.config(text=f"Cannot connect: {e}", fg="#f38ba8")
            return

        # 2. Send login — same as Client.login()
        mysend(self.socket, json.dumps({"action": "login", "name": name}))
        response = json.loads(myrecv(self.socket))

        if response["status"] == "ok":
            self.name = name
            self.sm = csm.ClientSM(self.socket)
            self.sm.set_state(S_LOGGEDIN)
            self.sm.set_myname(self.name)
            self.running = True
            self.login_frame.destroy()
            self._build_chat_screen()
            threading.Thread(target=self._recv_loop, daemon=True).start()

        elif response["status"] == "duplicate":
            self.socket.close()
            self.socket = None
            self.login_status.config(
                text="Name already taken — try another.", fg="#f38ba8"
            )

    # ─── Chat screen ─────────────────────────────────────────────────────────

    def _build_chat_screen(self):
        self.root.title(f"ICDS Chat  —  {self.name}")

        # top bar
        top = tk.Frame(self.root, bg="#181825", pady=8)
        top.pack(fill="x")

        tk.Label(
            top, text=f"  ● {self.name}",
            font=("Helvetica", 12, "bold"),
            bg="#181825", fg="#a6e3a1"
        ).pack(side="left")

        self.state_label = tk.Label(
            top, text="logged in",
            font=("Helvetica", 10),
            bg="#181825", fg="#6c7086"
        )
        self.state_label.pack(side="left", padx=8)
        toolbar = tk.Frame(self.root, bg="#1e1e2e", pady=4)
        toolbar.pack(fill="x", padx=8)

        tk.Button(
            toolbar, text="Who is online", font=("Helvetica", 9, "bold"),
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=lambda: self._send_quick_cmd("who")
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            toolbar, text="Time", font=("Helvetica", 9, "bold"),
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=lambda: self._send_quick_cmd("time")
        ).pack(side="left", padx=(0, 6))

        self.poem_var = tk.StringVar(value="18")
        tk.Entry(
            toolbar, textvariable=self.poem_var, font=("Helvetica", 10),
            width=5, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
            relief="flat", bd=4
        ).pack(side="left", padx=(12, 4))

        tk.Button(
            toolbar, text="Read Poem", font=("Helvetica", 9, "bold"),
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._send_poem
        ).pack(side="left", padx=(0, 6))
        # ==========================================

        self.msg_area = scrolledtext.ScrolledText(
            self.root,
            font=("Helvetica", 12),
            bg="#1e1e2e", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=0,
            state="disabled",
            wrap="word",
            padx=12, pady=8
        )
        self.msg_area.pack(fill="both", expand=True)

        self.msg_area.tag_config("self",   foreground="#89b4fa")
        self.msg_area.tag_config("peer",   foreground="#cdd6f4")
        self.msg_area.tag_config("system", foreground="#6c7086",
                                 font=("Helvetica", 10, "italic"))
        self.msg_area.tag_config("error",  foreground="#f38ba8")

        tk.Label(
            self.root,
            text="who · time · p<n> · ?<word> · c <name> · bye  |  or just type to chat",
            font=("Helvetica", 9), bg="#181825", fg="#585b70"
        ).pack(fill="x", padx=8)

        self.emoji_menu = tk.Menu(self.root, tearoff=0, bg="#313244", fg="#cdd6f4", font=("Helvetica", 12))
        emojis = ["(❁´◡`❁)", "(⌐■_■)", "(╯°□°）╯︵ ┻━┻", "¯\\_(ツ)_/¯", "ʕ•ᴥ•ʔ", "✧( ु•⌄• )", "(ಥ﹏ಥ)"]
        for emj in emojis:
            self.emoji_menu.add_command(label=emj, command=lambda e=emj: self._insert_emoji(e))

        bottom = tk.Frame(self.root, bg="#181825", pady=8)
        bottom.pack(fill="x", side="bottom")

        self.emoji_btn = tk.Button(
            bottom, text="😊",
            font=("Helvetica", 12),
            bg="#45475a", fg="#cdd6f4",
            activebackground="#585b70",
            relief="flat", bd=0, padx=10, pady=4,
            cursor="hand2",
            command=self._show_emoji_menu
        )
        self.emoji_btn.pack(side="left", padx=(10, 0))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            bottom, textvariable=self.input_var,
            font=("Helvetica", 12),
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=6
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=10)
        self.input_entry.bind("<Return>", lambda e: self._on_send())

        tk.Button(
            bottom, text="Send",
            font=("Helvetica", 11, "bold"),
            bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec",
            relief="flat", bd=0, padx=15, pady=4,
            cursor="hand2",
            command=self._on_send
        ).pack(side="right", padx=(0, 10))

        self._display("system", "Connected! Type 'who' to see who's online.\n")

    # ─── Display helper (thread-safe) ─────────────────────────────────────────

    def _display(self, tag: str, text: str):
        def _do():
            self.msg_area.config(state="normal")
            self.msg_area.insert("end", text, tag)
            self.msg_area.see("end")
            self.msg_area.config(state="disabled")
        self.root.after(0, _do)

    def _refresh_state_label(self):
        labels = {S_LOGGEDIN: "logged in", S_CHATTING: "chatting"}
        text = labels.get(self.sm.get_state(), "")
        self.root.after(0, lambda: self.state_label.config(text=text))

    # ========== 🌟 新增：Emoji 辅助函数 ==========
    
    def _show_emoji_menu(self):
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        self.emoji_menu.tk_popup(x, y)

    def _insert_emoji(self, emoji_str):
        current_text = self.input_var.get()
        self.input_var.set(current_text + emoji_str)
        self.input_entry.icursor("end")
        self.input_entry.focus()

    # ─── Send ─────────────────────────────────────────────────────────────────

    def _on_send(self):
        text = self.input_var.get().strip()
        if not text or not self.sm:
            return
        if self.sm.get_state() == S_OFFLINE:
            self.on_close()
            return
        self.input_var.set("")

        # Show the user's own message immediately
        if self.sm.get_state() == S_CHATTING:
            self._display("self", f"[{self.name}] {text}\n")
        else:
            self._display("self", f"> {text}\n")

        # Drive state machine — no incoming peer message
        # sm.proc(my_msg, peer_msg) matches your original signature
        out = self.sm.proc(text, "")
        if out:
            self._display("system", out + "\n")

        self._refresh_state_label()
 
    def _send_quick_cmd(self, cmd: str):
        self.input_var.set(cmd)
        self._on_send()

    def _send_poem(self):
        num = self.poem_var.get().strip()
        if num.isdigit():
            self._send_quick_cmd("p" + num)
        else:
            self._display("error", "[Error] Please enter a valid number for the poem!\n")
    # ====================================================

    # ─── Receive loop (background thread) ─────────────────────────────────────

    def _recv_loop(self):
        """
        Blocks waiting for server messages, then feeds them into
        the state machine as peer_msg (my_msg = "").
        """
        while self.running:
            try:
                peer_msg = myrecv(self.socket)
                if not peer_msg:
                    continue
            except Exception:
                if self.running:
                    self._display("error", "\nConnection lost.\n")
                break

            # Drive state machine with the incoming message
            out = self.sm.proc("", peer_msg)

            if out:
                # Colour chat messages differently from system notices
                try:
                    action = json.loads(peer_msg).get("action", "")
                except Exception:
                    action = ""
                tag = "peer" if action == "exchange" else "system"
                self._display(tag, out + "\n")

            self._refresh_state_label()

    # ─── Cleanup ─────────────────────────────────────────────────────────────

    def on_close(self):
        self.running = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except Exception:
                pass
        self.root.destroy()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ICDS GUI Chat Client")
    parser.add_argument("-d", "--host", default=None,
                        help="Server IP (default: localhost)")
    args = parser.parse_args()

    server_addr = (args.host, CHAT_PORT) if args.host else SERVER

    root = tk.Tk()
    app = GUIClient(root, server_addr)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()