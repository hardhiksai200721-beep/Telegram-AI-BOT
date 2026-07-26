import os
import json
import urllib.request

from http.server import BaseHTTPRequestHandler
from openai import OpenAI


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = json.dumps({
        "chat_id": chat_id,
        "text": text
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request) as response:
        return response.read()


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(
            json.dumps({
                "status": "Telegram AI Bot is running"
            }).encode("utf-8")
        )

    def do_POST(self):
        try:
            content_length = int(
                self.headers.get("Content-Length", 0)
            )

            body = self.rfile.read(content_length)

            update = json.loads(body.decode("utf-8"))

            message = update.get("message", {})

            chat = message.get("chat", {})
            chat_id = chat.get("id")

            user_message = message.get("text")

            if chat_id and user_message:

                if user_message == "/start":
                    reply = (
                        "Hello! 👋\n\n"
                        "I am your AI assistant powered by OpenRouter."
                    )

                else:
                    completion = client.chat.completions.create(
                        model="openrouter/free",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful AI assistant."
                            },
                            {
                                "role": "user",
                                "content": user_message
                            }
                        ]
                    )

                    reply = completion.choices[0].message.content

                send_telegram_message(chat_id, reply)

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json"
            )
            self.end_headers()

            self.wfile.write(
                json.dumps({"ok": True}).encode("utf-8")
            )

        except Exception as error:

            print("Webhook Error:", error)

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json"
            )
            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "ok": False,
                    "error": str(error)
                }).encode("utf-8")
            )