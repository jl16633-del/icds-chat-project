from textblob import TextBlob
import nltk


try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")


def analyze_sentiment(message: str):
    """
    Analyze the sentiment of a text message using TextBlob.
    Returns:
        label (str): "Positive", "Neutral", or "Negative"
        emoji (str): corresponding emoji
    """
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity  # range: [-1.0, 1.0]

    if polarity > 0.2:
        return "Positive", "😊"
    elif polarity < -0.2:
        return "Negative", "😡"
    else:
        return "Neutral", "😐"