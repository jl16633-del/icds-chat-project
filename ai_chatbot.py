from textblob import TextBlob

class AIChatBot:
    """
    Chatbot for ICDS Final Project
    Features:
    1. Basic chat response
    2. Conversation context memory
    3. Bonus: TextBlob sentiment analysis (Positive / Neutral / Negative)
    """
    
    def __init__(self):
        # Keep conversation history for context awareness
        self.conversation_history = []

    def analyze_sentiment(self, text: str) -> str:
        """
        Bonus Topic 3: Sentiment Analysis (Emotion Detection)
        Input: user message
        Output: positive / neutral / negative
        """
        score = TextBlob(text).sentiment.polarity
        if score > 0.1:
            return "positive"
        elif score < -0.1:
            return "negative"
        else:
            return "neutral"

    def get_response(self, user_input: str) -> dict:
        """
        Core chatbot function: generate reply and analyze sentiment
        Return format: {"response": "...", "sentiment": "..."}
        This format can be directly integrated into the chat system.
        """
        self.conversation_history.append(user_input)
        msg = user_input.lower().strip()

        # ------------------------------
        # Chatbot personality & replies
        # ------------------------------
        if "hello" in msg or "hi" in msg or "hey" in msg:
            reply = "Hello! I'm your AI chatbot. Nice to talk with you!"

        elif "how are you" in msg:
            reply = "I'm good! Thanks for asking. How about you?"

        elif "who are you" in msg:
            reply = "I'm an AI chatbot built for the ICDS distributed chat system."

        elif "bye" in msg or "goodbye" in msg:
            reply = "Goodbye! Have a wonderful day!"

        elif "what" in msg or "why" in msg or "how" in msg:
            reply = "That's a good question! I'm here to chat with you."

        else:
            reply = f"I received your message: {user_input}"

        # Get emotion result
        sentiment = self.analyze_sentiment(user_input)

        return {
            "response": reply,
            "sentiment": sentiment
        }