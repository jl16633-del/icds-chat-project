from ai_chatbot import AIChatBot

def main():
    bot = AIChatBot()
    print("=" * 50)
    print("🤖 AIChatBot Started")
    print("✅ Chatbot completed")
    print("✅ Sentiment Analysis Bonus completed")
    print("📌 Type 'exit' to quit")
    print("=" * 50)

    while True:
        user_msg = input("You: ")
        if user_msg.lower() == "exit":
            print("👋 Chat ended.")
            break

        res = bot.get_response(user_msg)
        print(f"Bot: {res['response']}")
        print(f"Sentiment: {res['sentiment']}\n")

if __name__ == "__main__":
    main()