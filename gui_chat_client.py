import tkinter as tk
from tkinter import scrolledtext, simpledialog
from tkinter import messagebox
import threading
import socket
import json
import argparse
from datetime import datetime
 
from chat_utils import mysend, myrecv, SERVER, CHAT_PORT, S_OFFLINE, S_LOGGEDIN, S_CHATTING
import client_state_machine as csm

import sys
import os

from ai_chatbot import AIChatBot
ai_bot = AIChatBot()

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from Gomoku.GUI import Chess_Board_Frame
except ImportError:
    try:
        from GUI import Chess_Board_Frame
    except ImportError as e:
        print(f"Failed loading: {e}")
 
def _now() -> str:
    return datetime.now().strftime("%H:%M")
 
 
class GUIClient:
 
    def __init__(self, root: tk.Tk, server_addr):
        self.root = root
        self.server_addr = server_addr
 
        self.socket = None
        self.sm = None
        self.name = ""
        self.running = False
 
        self.root.title("ICDS Chat")
        self.root.geometry("680x600")
        self.root.minsize(500, 400)          # now resizable
        self.root.configure(bg="#1e1e2e")
 
        self._build_login_screen()
        #Play button for the game
        self.game_btn = tk.Button(self.root, text="Start Playing Gomoku", command=self.open_gomoku)
        self.game_btn.pack(pady=5)
 
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
 
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(self.server_addr)
        except Exception as e:
            self.login_status.config(text=f"Cannot connect: {e}", fg="#f38ba8")
            return
 
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
 
        # ── top bar ──
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
 
        # ── toolbar ──
        toolbar = tk.Frame(self.root, bg="#181825", pady=6)
        toolbar.pack(fill="x")
 
        # left group: info commands
        left_group = tk.Frame(toolbar, bg="#181825")
        left_group.pack(side="left", padx=8)
 
        for label, cmd in [("Who", "who"), ("Time", "time")]:
            tk.Button(
                left_group, text=label,
                font=("Helvetica", 9, "bold"),
                bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                command=lambda c=cmd: self._send_quick_cmd(c)
            ).pack(side="left", padx=(0, 4))
 
        # separator
        tk.Frame(toolbar, bg="#45475a", width=1).pack(side="left", fill="y", padx=6)
 
        # middle group: connect
        mid_group = tk.Frame(toolbar, bg="#181825")
        mid_group.pack(side="left")
 
        tk.Button(
            mid_group, text="Connect to…",
            font=("Helvetica", 9, "bold"),
            bg="#a6e3a1", fg="#1e1e2e", activebackground="#94d5a0",
            relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
            command=self._open_connect_dialog
        ).pack(side="left", padx=(0, 4))
 
        tk.Button(
            mid_group, text="Leave chat",
            font=("Helvetica", 9, "bold"),
            bg="#f38ba8", fg="#1e1e2e", activebackground="#e07090",
            relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
            command=lambda: self._send_quick_cmd("bye")
        ).pack(side="left", padx=(0, 4))
 
        # separator
        tk.Frame(toolbar, bg="#45475a", width=1).pack(side="left", fill="y", padx=6)
 
        # right group: poem
        right_group = tk.Frame(toolbar, bg="#181825")
        right_group.pack(side="left")
 
        self.poem_var = tk.StringVar(value="18")
        tk.Entry(
            right_group, textvariable=self.poem_var,
            font=("Helvetica", 9), width=4,
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=4
        ).pack(side="left", padx=(0, 4))
 
        tk.Button(
            right_group, text="Poem",
            font=("Helvetica", 9, "bold"),
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
            command=self._send_poem
        ).pack(side="left")
 
        # ── search bar ──
        search_bar = tk.Frame(self.root, bg="#181825", pady=4)
        search_bar.pack(fill="x")
 
        tk.Label(
            search_bar, text="  Search history:",
            font=("Helvetica", 9), bg="#181825", fg="#6c7086"
        ).pack(side="left")
 
        self.search_var = tk.StringVar()
        tk.Entry(
            search_bar, textvariable=self.search_var,
            font=("Helvetica", 10), width=18,
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=4
        ).pack(side="left", padx=4)
 
        tk.Button(
            search_bar, text="Search",
            font=("Helvetica", 9, "bold"),
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._send_search
        ).pack(side="left")
 
        # ── visual divider ──
        tk.Frame(self.root, bg="#313244", height=1).pack(fill="x")
 
        # ── message area ──
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
 
        self.msg_area.tag_config("self",      foreground="#89b4fa")
        self.msg_area.tag_config("peer",      foreground="#cdd6f4")
        self.msg_area.tag_config("system",    foreground="#6c7086",
                                 font=("Helvetica", 10, "italic"))
        self.msg_area.tag_config("error",     foreground="#f38ba8")
        self.msg_area.tag_config("timestamp", foreground="#45475a",
                                 font=("Helvetica", 9))
 
        # ── visual divider ──
        tk.Frame(self.root, bg="#313244", height=1).pack(fill="x")
 
        # ── emoji + input ──
        self.emoji_menu = tk.Menu(
            self.root, tearoff=0,
            bg="#313244", fg="#cdd6f4", font=("Helvetica", 12)
        )
        for emj in ["(❁´◡`❁)", "(⌐■_■)", "(╯°□°）╯︵ ┻━┻",
                    "¯\\_(ツ)_/¯", "ʕ•ᴥ•ʔ", "✧( ु•⌄• )", "(ಥ﹏ಥ)"]:
            self.emoji_menu.add_command(
                label=emj, command=lambda e=emj: self._insert_emoji(e)
            )
 
        bottom = tk.Frame(self.root, bg="#181825", pady=8)
        bottom.pack(fill="x", side="bottom")
 
        tk.Button(
            bottom, text="😊",
            font=("Helvetica", 12),
            bg="#45475a", fg="#cdd6f4",
            activebackground="#585b70",
            relief="flat", bd=0, padx=10, pady=4,
            cursor="hand2",
            command=self._show_emoji_menu
        ).pack(side="left", padx=(10, 0))
 
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
        self.input_entry.focus()
 
        tk.Button(
            bottom, text="Send",
            font=("Helvetica", 11, "bold"),
            bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec",
            relief="flat", bd=0, padx=15, pady=4,
            cursor="hand2",
            command=self._on_send
        ).pack(side="right", padx=(0, 10))
 
        self._display("system", f"[{_now()}] Connected! Type or use the buttons above.\n")
 
    # ─── Display ─────────────────────────────────────────────────────────────
 
    def _display(self, tag: str, text: str):
        """Thread-safe append. Timestamps are embedded in text already."""
        def _do():
            self.msg_area.config(state="normal")
            self.msg_area.insert("end", text, tag)
            self.msg_area.see("end")
            self.msg_area.config(state="disabled")
        self.root.after(0, _do)
 
    def _display_with_ts(self, tag: str, text: str):
        """Prepend a muted timestamp then the message in its own colour."""
        def _do():
            self.msg_area.config(state="normal")
            self.msg_area.insert("end", f"[{_now()}] ", "timestamp")
            self.msg_area.insert("end", text + "\n", tag)
            self.msg_area.see("end")
            self.msg_area.config(state="disabled")
        self.root.after(0, _do)
 
    def _refresh_state_label(self):
        labels = {S_LOGGEDIN: "logged in", S_CHATTING: "chatting 💬"}
        text = labels.get(self.sm.get_state(), "")
        self.root.after(0, lambda: self.state_label.config(text=text))
 
    # ─── Emoji ───────────────────────────────────────────────────────────────
 
    def _show_emoji_menu(self):
        x = self.emoji_btn.winfo_rootx() if hasattr(self, "emoji_btn") else self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        self.emoji_menu.tk_popup(x, y)
 
    def _insert_emoji(self, emoji_str):
        self.input_var.set(self.input_var.get() + emoji_str)
        self.input_entry.icursor("end")
        self.input_entry.focus()
 
    # ─── Toolbar actions ─────────────────────────────────────────────────────
 
    def _send_quick_cmd(self, cmd: str):
        """Silently inject a command as if the user typed it."""
        self._display_with_ts("self", f"> {cmd}")
        out = self.sm.proc(cmd, "")
        if out:
            self._display_with_ts("system", out)
        if self.sm.get_state() == S_OFFLINE or "See you next time" in (out or ""):
            self.root.after(1000, self.on_close)
            return
        self._refresh_state_label()
 
    def _send_poem(self):
        num = self.poem_var.get().strip()
        if num.isdigit():
            self._send_quick_cmd("p" + num)
        else:
            self._display_with_ts("error", "[Error] Please enter a valid number for the poem.")
 
    def _send_search(self):
        word = self.search_var.get().strip()
        if word:
            self._send_quick_cmd(f"? {word}")
            self.search_var.set("")
        else:
            self._display_with_ts("error", "[Error] Please enter a keyword to search.")
 
    def _open_connect_dialog(self):
        """Pop up a small dialog asking for a name to connect to."""
        target = simpledialog.askstring(
            "Connect to user",
            "Enter the username to connect to:",
            parent=self.root
        )
        if target and target.strip():
            self._send_quick_cmd(f"c {target.strip()}")
 
    # ─── Send ─────────────────────────────────────────────────────────────────
 
    def _on_send(self):
        text = self.input_var.get().strip()
        if not text or not self.sm:
            return
        if self.sm.get_state() == S_OFFLINE:
            self.on_close()
            return
        self.input_var.set("")

        if text.startswith("@bot"):
            user_question = text.replace("@bot", "").strip()
            ai_response = ai_bot.get_response(user_question)

            self._display_with_ts("self", f"[{self.name}] {text}")
            self._display_with_ts("system", f"🤖 AI Bot: {ai_response['response']}")
            self._display_with_ts("system", f"💖 Sentiment: {ai_response['sentiment']}")
            return
                           
        if self.sm.get_state() == S_CHATTING:
            self._display_with_ts("self", f"[{self.name}] {text}")
        else:
            self._display_with_ts("self", f"> {text}")
 
        out = self.sm.proc(text, "")
        if out:
            self._display_with_ts("system", out)
 
        if self.sm.get_state() == S_OFFLINE or "See you next time" in (out or ""):
            self._display_with_ts("system", "[System] Closing connection…")
            self.root.after(1000, self.on_close)
            return
 
        self._refresh_state_label()
 
    # ─── Receive loop ─────────────────────────────────────────────────────────
 
    def _recv_loop(self):
        while self.running:
            try:
                peer_msg = myrecv(self.socket)
                if not peer_msg:
                    break
            except Exception:
                if self.running:
                    self._display_with_ts("error", "Connection lost.")
                break
 
            out = self.sm.proc("", peer_msg)
 
            if out:
                try:
                    action = json.loads(peer_msg).get("action", "")
                except Exception:
                    action = ""
                tag = "peer" if action == "exchange" else "system"
                self._display_with_ts(tag, out)
 
            self._refresh_state_label()
 
            if self.sm.get_state() == S_OFFLINE:
                self._display_with_ts("system", "[System] Connection closed.")
                self.root.after(1000, self.on_close)
                break
 
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
     
     # -- Game ------------------------------------------------------------------
 
    def open_gomoku(self):
        game_window = tk.Toplevel(self.root) 
        game_window.title("Gomoku Game")
        self.gui_chess_board = Chess_Board_Frame(game_window)
        self.gui_chess_board.pack()


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
