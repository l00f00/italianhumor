import requests
import time
import sys

TOKEN = "1227582427:AAFM_gwYUt3z3_XBBybUHCPs3JFxqU6bto"

def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        response = requests.get(url)
        data = response.json()
        if data["ok"] and data["result"]:
            # Get the chat ID from the last message
            chat_id = data["result"][-1]["message"]["chat"]["id"]
            print(f"FOUND_CHAT_ID={chat_id}")
            return chat_id
        else:
            print("No updates found. Please send a message to the bot first.")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    get_chat_id()
