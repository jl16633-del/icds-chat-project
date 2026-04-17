"""
Created on Sun Apr  5 00:00:32 2015

@author: zhengzhang
"""
from chat_utils import *
import json

class ClientSM:
    def __init__(self, s):
        self.state = S_OFFLINE
        self.peer = ''
        self.me = ''
        self.out_msg = ''
        self.s = s
        self.pending_peer = ''  # 新增：记住我们正在尝试连接的人

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    def connect_to(self, peer):
        # 异步化：只发送请求，不在这里死等 myrecv
        self.pending_peer = peer
        msg = json.dumps({"action": "connect", "target": peer})
        mysend(self.s, msg)

    def disconnect(self):
        msg = json.dumps({"action": "disconnect"})
        mysend(self.s, msg)
        self.out_msg += 'You are disconnected from ' + self.peer + '\n'
        self.peer = ''

    def proc(self, my_msg, peer_msg):
        self.out_msg = ''
# ==============================================================================
# Once logged in, do a few things: get peer listing, connect, search
# And, of course, if you are so bored, just go
# This is event handling instate "S_LOGGEDIN"
# ==============================================================================
        if self.state == S_LOGGEDIN:
            if len(my_msg) > 0:
                if my_msg == 'q':
                    self.out_msg += 'See you next time!\n'
                    self.state = S_OFFLINE

                elif my_msg == 'time':
                    mysend(self.s, json.dumps({"action": "time"}))

                elif my_msg == 'who':
                    mysend(self.s, json.dumps({"action": "list"}))

                elif my_msg[0] == 'c':
                    peer = my_msg[1:].strip()
                    self.connect_to(peer)

                elif my_msg[0] == '?':
                    term = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action": "search", "target": term}))

                elif my_msg[0] == 'p' and my_msg[1:].isdigit():
                    poem_idx = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action": "poem", "target": poem_idx}))

                else:
                    self.out_msg += menu

            if len(peer_msg) > 0:
                try:
                    peer_msg = json.loads(peer_msg)
                except Exception as err:
                    self.out_msg += " json.loads failed " + str(err)
                    return self.out_msg

                if peer_msg.get("action") == "connect" and "from" in peer_msg:
                    self.peer = peer_msg["from"]
                    self.out_msg += 'Request from ' + self.peer + '\n'
                    self.out_msg += 'You are connected with ' + self.peer + '. Chat away!\n\n'
                    self.out_msg += '-----------------------------------\n'
                    self.state = S_CHATTING

                elif "status" in peer_msg:
                    if peer_msg["status"] == "success":
                        self.peer = self.pending_peer
                        self.state = S_CHATTING
                        self.out_msg += 'Connect to ' + self.peer + '. Chat away!\n\n'
                        self.out_msg += '-----------------------------------\n'
                    elif peer_msg["status"] == "busy":
                        self.out_msg += 'User is busy. Please try again later\n'
                    elif peer_msg["status"] == "self":
                        self.out_msg += 'Cannot talk to yourself (sick)\n'
                    else:
                        self.out_msg += 'User is not online, try again later\n'

                elif "results" in peer_msg:
                    res = peer_msg.get("results", "").strip()
                    if len(res) > 0:
                        self.out_msg += "==== 🔍 Search/Query Results ====\n" + res + '\n\n'
                    else:
                        self.out_msg += "[System]: 📭 No results found (no chat history matches).\n\n"

# ==============================================================================
# Start chatting, 'bye' for quit
# This is event handling instate "S_CHATTING"
# ==============================================================================
        elif self.state == S_CHATTING:
            if len(my_msg) > 0:     # my stuff going out
                mysend(self.s, json.dumps({"action": "exchange", "from": "[" + self.me + "]", "message": my_msg}))
                if my_msg == 'bye':
                    self.disconnect()
                    self.state = S_LOGGEDIN
                    self.peer = ''
                    
            if len(peer_msg) > 0:    # peer's stuff, coming in
                try:
                    peer_msg = json.loads(peer_msg)
                except Exception as err:
                    self.out_msg += " json.loads failed " + str(err)
                    return self.out_msg

                if peer_msg["action"] == "exchange":
                    self.out_msg += peer_msg["from"] + peer_msg["message"] + '\n'
     
                elif peer_msg["action"] == "connect":
                    self.out_msg += "(" + peer_msg["from"] + " joined)\n"

                elif peer_msg["action"] == "disconnect":
                    msg_text = peer_msg.get("msg", peer_msg.get("from", "someone") + " left the chat")
                    self.out_msg += msg_text + '\n'
                    self.state = S_LOGGEDIN

            # Display the menu again
            if self.state == S_LOGGEDIN:
                self.out_msg += menu
# ==============================================================================
# invalid state
# ==============================================================================
        else:
            self.out_msg += 'How did you wind up here??\n'
            print_state(self.state)

        return self.out_msg