from chat_bot_client import ChatBotClient

class AIChatBot:
    def __init__(self):
        self.bot = ChatBotClient(model="llama3")
        self.personality = "friendly"
        self.conversation_history = []
        self.max_history = 10

    def set_personality(self, mode):
        if mode in ["friendly", "formal", "humorous"]:
            self.personality = mode

    def _apply_personality(self, raw):
        if self.personality == "friendly":
            return "😊 " + raw
        elif self.personality == "formal":
            return "Dear user, " + raw
        elif self.personality == "humorous":
            return "😜 " + raw
        return raw

    def _update_history(self, user_msg, bot_msg):
        self.conversation_history.append("You: " + user_msg)
        self.conversation_history.append("Bot: " + bot_msg)
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history.pop(0)
            self.conversation_history.pop(0)

    def get_response(self, user_input):
        raw_reply = self.bot.chat(user_input)
        final_reply = self._apply_personality(raw_reply)
        self._update_history(user_input, final_reply)
        return {
            "response": final_reply,
            "sentiment": "neutral"
        }

    def clear_context(self):
        self.conversation_history.clear()