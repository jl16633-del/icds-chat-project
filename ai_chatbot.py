# 异常兼容处理：适配所有组员电脑环境，无textblob库也不会程序崩溃
try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

class AIChatBot:
    def __init__(self):
        # 初始化聊天机器人本体
        self.chatbot = ChatBot(
            "ICDS Chat Bot",
            storage_adapter="chatterbot.storage.SQLStorageAdapter",
            logic_adapters=[
                "chatterbot.logic.BestMatch"
            ]
        )
        # 内置基础对话训练语料
        train_data = [
            "Hello",
            "Hello! How can I help you today?",
            "Hi",
            "Hi there!",
            "How are you?",
            "I'm just an AI bot, I'm always fine!",
            "Thank you",
            "You are welcome!",
            "Bye",
            "Goodbye! Have a nice day."
        ]
        trainer = ListTrainer(self.chatbot)
        trainer.train(train_data)

    def get_response(self, user_input):
        # 获取AI对话回复
        bot_reply = self.chatbot.get_response(user_input)

        # 只有环境安装了textblob库，才执行情感分析
        if HAS_TEXTBLOB:
            sentiment_score = TextBlob(user_input).sentiment.polarity
            if sentiment_score > 0.1:
                sentiment = "positive"
            elif sentiment_score < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
        # 没安装库的电脑，友好提示，绝对不报错、不崩溃
        else:
            sentiment = "unavailable (dependency not installed)"

        return {
            "response": str(bot_reply),
            "sentiment": sentiment
        }