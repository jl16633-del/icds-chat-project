from chat_bot_client import ChatBotClient
from sentiment_tools import analyze_sentiment

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

    def get_response(self, user_input, raw_text=None):
        raw_reply = self.bot.chat(user_input)
        final_reply = self._apply_personality(raw_reply)

        text_to_analyze = raw_text if raw_text else user_input
        sentiment_label, sentiment_emoji = analyze_sentiment(text_to_analyze)
        sentiment = sentiment_label.lower()

        self._update_history(text_to_analyze, final_reply)
        return {
            "response": final_reply,
            "sentiment": sentiment
        }

    def clear_context(self):
        self.conversation_history.clear()