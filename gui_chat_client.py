import tkinter as tk
from tkinter import scrolledtext, simpledialog
from tkinter import messagebox
import threading
import socket
import json
import argparse
from datetime import datetime
import tkinter.font as tkFont
 
from chat_utils import mysend, myrecv, SERVER, CHAT_PORT, S_OFFLINE, S_LOGGEDIN, S_CHATTING
import client_state_machine as csm

import sys
import os

from ai_chatbot import AIChatBot
ai_bot = AIChatBot()

import requests
import urllib.parse
from io import BytesIO
from PIL import Image, ImageTk

from nlp_tools import extract_keywords_yake, summarize_with_sumy

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

        self.image_cache = []
        self.chat_history = []
        self.bot_in_chat = False

        # Unified font settings - scale up everything
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=18) 
        text_font = tkFont.nametofont("TkTextFont")
        text_font.configure(size=18)   
        fixed_font = tkFont.nametofont("TkFixedFont")
        fixed_font.configure(size=18)    
     
        self.root.title("ICDS Chat")
        self.root.geometry("1050x800") 
        self.root.minsize(800, 600)
        self.root.configure(bg="#1e1e2e")
 
        self._build_login_screen()
        self.game_btn = tk.Button(self.root, text="Start Playing Gomoku", command=self.open_gomoku,
                                 font=("Helvetica", 16, "bold")) 
        self.game_btn.pack(pady=10)
 
    # ─── Login screen ────────────────────────────────────────────────────────
 
    def _build_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg="#1e1e2e")
        self.login_frame.pack(expand=True)
 
        tk.Label(
            self.login_frame, text="ICDS Chat",
            font=("Helvetica", 32, "bold"),  
            bg="#1e1e2e", fg="#cdd6f4"
        ).pack(pady=(50, 10))
 
        tk.Label(
            self.login_frame, text="Enter your nickname",
            font=("Helvetica", 16), 
            bg="#1e1e2e", fg="#6c7086"
        ).pack(pady=(0, 30))
 
        self.name_var = tk.StringVar()
        entry = tk.Entry(
            self.login_frame, textvariable=self.name_var,
            font=("Helvetica", 18), 
            width=25,  
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=6
        )
        entry.pack(pady=10)
        entry.focus()
        entry.bind("<Return>", lambda e: self._do_login())
 
        tk.Button(
            self.login_frame, text="Join",
            font=("Helvetica", 16, "bold"), 
            bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec",
            relief="flat", bd=0, padx=30, pady=10,  
            cursor="hand2",
            command=self._do_login
        ).pack(pady=20)
 
        self.login_status = tk.Label(
            self.login_frame, text="",
            font=("Helvetica", 14),  
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
        top = tk.Frame(self.root, bg="#181825", pady=10)
        top.pack(fill="x")
 
        tk.Label(
            top, text=f"  ● {self.name}",
            font=("Helvetica", 16, "bold"),  
            bg="#181825", fg="#a6e3a1"
        ).pack(side="left")
 
        self.state_label = tk.Label(
            top, text="logged in",
            font=("Helvetica", 14),
            bg="#181825", fg="#6c7086"
        )
        self.state_label.pack(side="left", padx=12)
 
        # ── toolbar ──
        toolbar = tk.Frame(self.root, bg="#181825", pady=8)
        toolbar.pack(fill="x")
 
        # left group: info commands
        left_group = tk.Frame(toolbar, bg="#181825")
        left_group.pack(side="left", padx=12)
 
        for label, cmd in [("Who", "who"), ("Time", "time")]:
            tk.Button(
                left_group, text=label,
                font=("Helvetica", 12, "bold"), 
                bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                relief="flat", bd=0, padx=15, pady=6,  
                cursor="hand2",
                command=lambda c=cmd: self._send_quick_cmd(c)
            ).pack(side="left", padx=(0, 6))
 
        # separator
        tk.Frame(toolbar, bg="#45475a", width=2).pack(side="left", fill="y", padx=8)
 
        # middle group: connect
        mid_group = tk.Frame(toolbar, bg="#181825")
        mid_group.pack(side="left")
 
        tk.Button(
            mid_group, text="Connect to…",
            font=("Helvetica", 12, "bold"), 
            bg="#a6e3a1", fg="#1e1e2e", activebackground="#94d5a0",
            relief="flat", bd=0, padx=15, pady=6,  
            cursor="hand2",
            command=self._open_connect_dialog
        ).pack(side="left", padx=(0, 6))
 
        tk.Button(
            mid_group, text="Leave chat",
            font=("Helvetica", 12, "bold"), 
            bg="#f38ba8", fg="#1e1e2e", activebackground="#e07090",
            relief="flat", bd=0, padx=15, pady=6,  
            cursor="hand2",
            command=lambda: self._send_quick_cmd("bye")
        ).pack(side="left", padx=(0, 6))
 
        # separator
        tk.Frame(toolbar, bg="#45475a", width=2).pack(side="left", fill="y", padx=8)
 
        # right group: poem
        right_group = tk.Frame(toolbar, bg="#181825")
        right_group.pack(side="left")
 
        self.poem_var = tk.StringVar(value="18")
        tk.Entry(
            right_group, textvariable=self.poem_var,
            font=("Helvetica", 12),  
            width=5,
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=4
        ).pack(side="left", padx=(0, 6))
 
        tk.Button(
            right_group, text="Poem",
            font=("Helvetica", 12, "bold"), 
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", bd=0, padx=15, pady=6,  
            cursor="hand2",
            command=self._send_poem
        ).pack(side="left")

        # ── separator ──
        tk.Frame(toolbar, bg="#45475a", width=2).pack(side="left", fill="y", padx=8)

        # ── NLP group (Bonus Topic 2) ─────────────────────────────────────────
        nlp_group = tk.Frame(toolbar, bg="#181825")
        nlp_group.pack(side="left")

        tk.Button(
            nlp_group, text="keywords",
            font=("Helvetica", 12, "bold"),  
            bg="#cba6f7", fg="#1e1e2e", activebackground="#b48fd4",
            relief="flat", bd=0, padx=15, pady=6, 
            cursor="hand2",
            command=self._run_keywords
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            nlp_group, text="summary",
            font=("Helvetica", 12, "bold"), 
            bg="#cba6f7", fg="#1e1e2e", activebackground="#b48fd4",
            relief="flat", bd=0, padx=15, pady=6, 
            cursor="hand2",
            command=self._run_summary
        ).pack(side="left")
        # ─────────────────────────────────────────────────────────────────────

        bot_group = tk.Frame(toolbar, bg="#181825")
        bot_group.pack(side="left")

        self.bot_btn = tk.Button(
            bot_group, text="🤖 Bot: OFF",
            font=("Helvetica", 12, "bold"),
            bg="#fab387", fg="#1e1e2e", activebackground="#f9e2af",
            relief="flat", bd=0, padx=15, pady=6,
            cursor="hand2",
            command=self._toggle_bot_invite
        )
        self.bot_btn.pack(side="left", padx=(0, 6))
        
        # ── search bar ──
        search_bar = tk.Frame(self.root, bg="#181825", pady=6)
        search_bar.pack(fill="x")
 
        tk.Label(
            search_bar, text="  Search history:",
            font=("Helvetica", 12), 
            bg="#181825", fg="#6c7086"
        ).pack(side="left")
 
        self.search_var = tk.StringVar()
        tk.Entry(
            search_bar, textvariable=self.search_var,
            font=("Helvetica", 14), 
            width=20,
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=4
        ).pack(side="left", padx=6)
 
        tk.Button(
            search_bar, text="Search",
            font=("Helvetica", 12, "bold"), 
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", bd=0, padx=12, pady=4, 
            cursor="hand2",
            command=self._send_search
        ).pack(side="left")
 
        # ── visual divider ──
        tk.Frame(self.root, bg="#313244", height=2).pack(fill="x")
 
        # ── message area ──
        self.msg_area = scrolledtext.ScrolledText(
            self.root,
            font=("Helvetica", 16),  
            bg="#1e1e2e", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=0,
            state="disabled",
            wrap="word",
            padx=16, pady=12  
        )
        self.msg_area.pack(fill="both", expand=True)
 
        self.msg_area.tag_config("self",      foreground="#89b4fa")
        self.msg_area.tag_config("peer",      foreground="#cdd6f4")
        self.msg_area.tag_config("system",    foreground="#6c7086",
                                 font=("Helvetica", 14, "italic"))  
        self.msg_area.tag_config("error",     foreground="#f38ba8")
        self.msg_area.tag_config("timestamp", foreground="#45475a",
                                 font=("Helvetica", 12)) 
 
        # ── visual divider ──
        tk.Frame(self.root, bg="#313244", height=2).pack(fill="x")
 
        # ── emoji + input ──
        self.emoji_menu = tk.Menu(
            self.root, tearoff=0,
            bg="#313244", fg="#cdd6f4", font=("Helvetica", 16)  
        )
        for emj in ["(❁´◡`❁)", "(⌐■_■)", "(╯°□°）╯︵ ┻━┻",
                    "¯\\_(ツ)_/¯", "ʕ•ᴥ•ʔ", "✧( ु•⌄• )", "(ಥ﹏ಥ)"]:
            self.emoji_menu.add_command(
                label=emj, command=lambda e=emj: self._insert_emoji(e)
            )
 
        bottom = tk.Frame(self.root, bg="#181825", pady=12)
        bottom.pack(fill="x", side="bottom")
 
        tk.Button(
            bottom, text="😊",
            font=("Helvetica", 16),  
            bg="#45475a", fg="#cdd6f4",
            activebackground="#585b70",
            relief="flat", bd=0, padx=15, pady=8, 
            cursor="hand2",
            command=self._show_emoji_menu
        ).pack(side="left", padx=(15, 0))
 
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            bottom, textvariable=self.input_var,
            font=("Helvetica", 16),  
            bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat", bd=6
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=15)
        self.input_entry.bind("<Return>", lambda e: self._on_send())
        self.input_entry.focus()

        btn_frame = tk.Frame(bottom, bg="#181825")
        btn_frame.pack(side="right", padx=(0,15))
        
 
        tk.Button(
            btn_frame, text="Send",
            font=("Helvetica", 14, "bold"), 
            bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec",
            relief="flat", bd=0, padx=20, pady=8,  
            cursor="hand2",
            command=self._on_send
        ).pack(side="left")
 
        self._display("system", f"[{_now()}] Connected! Type or use the buttons above.\n")
    
    # ─── Display ─────────────────────────────────────────────────────────────
 
    def _display(self, tag: str, text: str):
        def _do():
            self.msg_area.config(state="normal")
            self.msg_area.insert("end", text, tag)
            self.msg_area.see("end")
            self.msg_area.config(state="disabled")
        self.root.after(0, _do)
 
    def _display_with_ts(self, tag: str, text: str):
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
        target = simpledialog.askstring(
            "Connect to user",
            "Enter the username to connect to:",
            parent=self.root
        )
        if target and target.strip():
            self._send_quick_cmd(f"c {target.strip()}")

    # ─── NLP actions (Bonus Topic 2) ─────────────────────────────────────────

    def _run_keywords(self):
        if not self.chat_history:
            self._display_with_ts("system", "📭 No chat history to analyze yet.")
            return
        self._display_with_ts("system", "🔍 Extracting keywords…")
        threading.Thread(target=self._do_keywords, daemon=True).start()

    def _do_keywords(self):
        try:
            keywords = extract_keywords_yake(self.chat_history, top_k=5)
            if keywords:
                result = "🏷️ Keywords:  " + "  |  ".join(keywords)
            else:
                result = "🏷️ Keywords: (no result)"
        except Exception as e:
            result = f"❌ Keywords error: {e}"
        self._display_with_ts("system", result)

    def _run_summary(self):
        if not self.chat_history:
            self._display_with_ts("system", "📭 No chat history to analyze yet.")
            return
        self._display_with_ts("system", "📝 Generating summary…")
        threading.Thread(target=self._do_summary, daemon=True).start()

    def _do_summary(self):
        try:
            sentences = summarize_with_sumy(self.chat_history, sentences_count=3)
            if sentences:
                result = "📋 Summary:\n" + "\n".join(f"  • {s}" for s in sentences)
            else:
                result = "📋 Summary: (not enough content to summarize)"
        except Exception as e:
            result = f"❌ Summary error: {e}"
        self._display_with_ts("system", result)

    # ─────────────────────────────────────────────────────────────────────────
 
    # ─── Send ─────────────────────────────────────────────────────────────────
    def _toggle_bot_invite(self):
        self.bot_in_chat = not self.bot_in_chat
        status = "ON" if self.bot_in_chat else "OFF"
        color = "#a6e3a1" if self.bot_in_chat else "#fab387"
        self.bot_btn.config(text=f"🤖 Bot: {status}", bg=color)
        
        msg = "🤖 Bot has joined the chat!" if self.bot_in_chat else "🤖 Bot has left."
        self._display_with_ts("system", msg)
        if self.sm.get_state() == S_CHATTING:
             self.sm.proc(msg, "")

    def _on_send(self):
        text = self.input_var.get().strip()
        if not text: return
        self.input_var.set("")

        if text.strip() == "/keywords": self._run_keywords(); return
        if text.strip() == "/summary": self._run_summary(); return

        is_bot_msg = self.bot_in_chat or text.startswith("@bot")
        
        # Send message to state machine/network
        out = self.sm.proc(text, "") 
        
        # Display in own window
        msg_text = f"[{self.name}] {text}"
        self._display_with_ts("self", msg_text)
        self.chat_history.append(msg_text)
        
        # Display state machine feedback (and block the spammy menu in bot mode)
        if out:
            if is_bot_msg and "++++ Choose one of the following commands" in out:
                pass 
            else:
                self._display_with_ts("system", out)

        # Clean up potential @bot prefix to get pure text for AI processing
        user_content = text.replace("@bot", "").strip() if text.startswith("@bot") else text
        if not user_content: user_content = "hello"

        # Start background thread for sentiment analysis (and get bot reply if triggered)
        threading.Thread(target=self._process_text_with_ai, args=(user_content, is_bot_msg), daemon=True).start()
    
    def _process_text_with_ai(self, text, is_bot_msg):
        try:
            self.root.after(0, lambda: self._display_with_ts("system", "⏳ AI is processing..."))
            
            # Call your AI bot interface here
            ai_response = ai_bot.get_response(text)
            sentiment = ai_response.get('sentiment', 'Unknown')
            
            # Step 1: Print sentiment analysis for the message, regardless of bot mode
            self.root.after(0, lambda: self._display_with_ts("system", f"💖 Sentiment: {sentiment}"))

            # Step 2: If the user is talking to the bot, print the bot's reply and send it to the chat
            if is_bot_msg:
                bot_reply = ai_response.get('response', '')
                full_bot_msg = f"🤖 [AI Bot]: {bot_reply}"

                if self.sm.get_state() == S_CHATTING:
                    self.sm.proc(full_bot_msg, "")
                
                self.root.after(0, lambda: self._display_with_ts("system", full_bot_msg))
                self.chat_history.append(full_bot_msg)
                
        except Exception as e:
            self.root.after(0, lambda: self._display_with_ts("error", f"❌ AI/Sentiment error: {e}"))
 
    # ─── Receive loop ─────────────────────────────────────────────────────────
 
    def _recv_loop(self):
        while self.running:
            try:
                peer_msg = myrecv(self.socket)
                if not peer_msg:
                    break
                try:
                    msg_data = json.loads(peer_msg)
                    action = msg_data.get("action")
                    if action in ["game_move", "game_request", "game_accept", "game_reject"]:
                        if action == "game_move":
                            x, y = msg_data["location"]
                            if hasattr(self, 'gui_chess_board') and self.gui_chess_board:
                                self.root.after(0, lambda i=x, j=y: self.gui_chess_board.chess_board_canvas.draw_remote_move(i, j))
                        elif action == "game_request":
                            self.root.after(0, self.handle_game_request)
                        elif action == "game_accept":
                            self.root.after(0, self.handle_game_accept)
                        elif action == "game_reject":
                            self.root.after(0, lambda: messagebox.showinfo("Invitation Result", "The other player cruelly rejected your game invitation."))
                        continue
                except Exception:
                    pass

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
                if tag == "peer":
                    self.chat_history.append(out)      
 
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
     
    # ─── Game ─────────────────────────────────────────────────────────────────

    def send_msg(self, msg_obj):
        mysend(self.socket, json.dumps(msg_obj))
     
    def open_gomoku(self):
        if self.sm.get_state() != S_CHATTING:
            choice = messagebox.askyesno("Single player mode", "No friends connected!\nOpen Single player mode?")
            if choice:
                self.launch_single_player()
            return
         
        choice = messagebox.askyesnocancel("Choose mode", "[Yes] Invite the other player\n[No] Start single player mode")
        if choice is None:
            return
        if choice:  
            self.send_msg({"action": "game_request"})
            messagebox.showinfo("Request sent", "Waiting...")
        else: 
            self.launch_single_player()

    def handle_game_request(self):
        choice = messagebox.askyesno("Game invitation", "Your friend is inviting you to play Gomoku. Do you want to accept?")
        if choice:
            self.send_msg({"action": "game_accept"}) 
            self.launch_multiplayer()             
        else:
            self.send_msg({"action": "game_reject"})

    def handle_game_accept(self):
        messagebox.showinfo("Accept", "Your friend has accepted the invitation, game starts!")
        self.launch_multiplayer()

    def launch_single_player(self):
        game_window = tk.Toplevel(self.root)
        game_window.title("Gomoku - Single Player mode")
        self.gui_chess_board = Chess_Board_Frame(game_window, network_client=None)
        self.gui_chess_board.pack()

    def launch_multiplayer(self):
        game_window = tk.Toplevel(self.root)
        game_window.title("Gomoku - Multiplayer mode")
        self.gui_chess_board = Chess_Board_Frame(game_window, network_client=self)
        self.gui_chess_board.pack()
     
    # ─── Bonus Topic 1: AI Picture Generation ────────────────────────────────

    def handle_aipic(self, prompt):
        self._display_with_ts("system", f"🎨 Picture is being generated: '{prompt}', Please wait…")
        threading.Thread(target=self._fetch_and_display_image, args=(prompt,), daemon=True).start()

    def _fetch_and_display_image(self, prompt):
        try:
            safe_prompt = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=400&height=400&nologo=true"
            print(f"[DEBUG] Request URL: {url}")
            response = requests.get(url, timeout=30)
            print(f"[DEBUG] Response status: {response.status_code}")
            if response.status_code == 200:
                image_data = Image.open(BytesIO(response.content))
                image_data.thumbnail((300, 300))
                photo = ImageTk.PhotoImage(image_data)
                self.image_cache.append(photo)
                self.root.after(0, lambda p=photo: self._insert_image_to_chat(p))
            else:
                print(f"[DEBUG] Response body: {response.text[:200]}")
                self.root.after(0, lambda: self._display_with_ts("error", f"❌ Failed, status code: {response.status_code}"))
        except Exception as e:
            print(f"[DEBUG] Exception: {type(e).__name__}: {e}")
            self.root.after(0, lambda: self._display_with_ts("error", f"❌ Network error: {e}"))
            
    def _insert_image_to_chat(self, photo):
        self.msg_area.config(state="normal")
        self.msg_area.insert("end", "\n[AI Generated Picture]:\n")
        self.msg_area.image_create("end", image=photo)
        self.msg_area.insert("end", "\n\n")
        self.msg_area.see("end")
        self.msg_area.config(state="disabled")


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