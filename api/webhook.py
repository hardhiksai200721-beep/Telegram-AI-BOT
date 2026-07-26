import os
import json
import base64
import urllib.request

from http.server import BaseHTTPRequestHandler
from openai import OpenAI


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")


# =========================================================
# OPENROUTER CLIENT
# =========================================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


# =========================================================
# TELEGRAM - SEND MESSAGE
# =========================================================

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    # First try Markdown formatting
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(request) as response:
            return response.read()

    except Exception:
        # If Markdown fails, send as normal text
        fallback_data = json.dumps({
            "chat_id": chat_id,
            "text": text
        }).encode("utf-8")

        fallback_request = urllib.request.Request(
            url,
            data=fallback_data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(fallback_request) as response:
            return response.read()


# =========================================================
# TELEGRAM - TYPING INDICATOR
# =========================================================

def send_typing_action(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction"

    data = json.dumps({
        "chat_id": chat_id,
        "action": "typing"
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        urllib.request.urlopen(request).read()

    except Exception:
        pass


# =========================================================
# TELEGRAM - DOWNLOAD FILE
# =========================================================

def get_telegram_file(file_id):

    # Ask Telegram for the file path
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
        f"?file_id={file_id}"
    )

    with urllib.request.urlopen(url) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    file_path = result["result"]["file_path"]

    # Download the actual file
    download_url = (
        f"https://api.telegram.org/file/"
        f"bot{TELEGRAM_TOKEN}/{file_path}"
    )

    with urllib.request.urlopen(download_url) as response:
        file_data = response.read()

    return file_data, file_path


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a helpful AI assistant responding through Telegram.

Write answers in a clean, modern, ChatGPT-like style.

Formatting rules:

- Start directly with the answer.
- Use clear headings when they improve readability.
- Use short paragraphs.
- Use bullet points for lists.
- Use numbered steps for procedures.
- Highlight important words using **bold**.
- Put programming code inside triple-backtick code blocks.
- Include examples when useful.
- Avoid unnecessary repetition.
- Use emojis sparingly and only when they improve clarity.
- For simple questions, give concise answers.
- For technical or complex questions, provide a structured explanation.

When analyzing images:

- Carefully inspect the image.
- Describe important visible information.
- Read visible text when possible.
- Explain screenshots, diagrams, errors, objects, or scenes.
- If something cannot be determined reliably, say so instead of guessing.
"""


# =========================================================
# VERCEL WEBHOOK
# =========================================================

class handler(BaseHTTPRequestHandler):

    # -----------------------------------------------------
    # GET REQUEST
    # -----------------------------------------------------

    def do_GET(self):

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/json"
        )
        self.end_headers()

        self.wfile.write(
            json.dumps({
                "status": "Telegram AI Bot is running"
            }).encode("utf-8")
        )


    # -----------------------------------------------------
    # POST REQUEST FROM TELEGRAM
    # -----------------------------------------------------

    def do_POST(self):

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                content_length
            )

            update = json.loads(
                body.decode("utf-8")
            )

            message = update.get(
                "message",
                {}
            )

            chat = message.get(
                "chat",
                {}
            )

            chat_id = chat.get("id")

            # ---------------------------------------------
            # Detect Telegram message types
            # ---------------------------------------------

            user_message = message.get("text")

            photos = message.get(
                "photo",
                []
            )

            document = message.get(
                "document"
            )

            caption = message.get(
                "caption",
                ""
            )


            # ---------------------------------------------
            # Process supported messages
            # ---------------------------------------------

            if chat_id and (
                user_message
                or photos
                or document
            ):

                # -----------------------------------------
                # /start command
                # -----------------------------------------

                if user_message == "/start":

                    reply = (
                        "Hello! 👋\n\n"
                        "I am your AI assistant powered "
                        "by OpenRouter.\n\n"
                        "You can send me text questions "
                        "or images for analysis."
                    )


                # -----------------------------------------
                # IMAGE MESSAGE
                # -----------------------------------------

                elif photos:

                    send_typing_action(
                        chat_id
                    )

                    # Telegram provides multiple sizes.
                    # The final one is generally the
                    # largest available version.
                    file_id = photos[-1][
                        "file_id"
                    ]

                    image_data, file_path = (
                        get_telegram_file(
                            file_id
                        )
                    )

                    # Convert image to Base64
                    encoded_image = (
                        base64.b64encode(
                            image_data
                        ).decode("utf-8")
                    )

                    # -------------------------------------
                    # Determine image MIME type
                    # -------------------------------------

                    extension = (
                        file_path
                        .lower()
                        .split(".")[-1]
                    )

                    if extension == "png":

                        mime_type = (
                            "image/png"
                        )

                    elif extension == "webp":

                        mime_type = (
                            "image/webp"
                        )

                    else:

                        mime_type = (
                            "image/jpeg"
                        )


                    # -------------------------------------
                    # Build Base64 image URL
                    # -------------------------------------

                    image_url = (
                        f"data:{mime_type};"
                        f"base64,{encoded_image}"
                    )


                    # -------------------------------------
                    # Use caption as image question
                    # -------------------------------------

                    if caption:

                        image_prompt = caption

                    else:

                        image_prompt = (
                            "Describe and explain "
                            "what is shown in this image."
                        )


                    # -------------------------------------
                    # Send image to Gemma
                    # -------------------------------------

                    completion = (
                        client.chat.completions.create(

                            model=(
                                "google/"
                                "gemma-4-26b-a4b-it:free"
                            ),

                            max_tokens=700,

                            messages=[
                                {
                                    "role": "system",
                                    "content": SYSTEM_PROMPT
                                },
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": image_prompt
                                        },
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": image_url
                                            }
                                        }
                                    ]
                                }
                            ]
                        )
                    )

                    reply = (
                        completion
                        .choices[0]
                        .message
                        .content
                    )


                # -----------------------------------------
                # DOCUMENT
                # -----------------------------------------

                elif document:

                    reply = (
                        "📄 I detected your file.\n\n"
                        "Document analysis is being "
                        "added next. For now, please "
                        "send text or an image."
                    )


                # -----------------------------------------
                # NORMAL TEXT MESSAGE
                # -----------------------------------------

                else:

                    send_typing_action(
                        chat_id
                    )

                    completion = (
                        client.chat.completions.create(

                            model=(
                                "google/"
                                "gemma-4-26b-a4b-it:free"
                            ),

                            max_tokens=700,

                            messages=[
                                {
                                    "role": "system",
                                    "content": SYSTEM_PROMPT
                                },
                                {
                                    "role": "user",
                                    "content": user_message
                                }
                            ]
                        )
                    )

                    reply = (
                        completion
                        .choices[0]
                        .message
                        .content
                    )


                # -----------------------------------------
                # Send final answer to Telegram
                # -----------------------------------------

                send_telegram_message(
                    chat_id,
                    reply
                )


            # ---------------------------------------------
            # Tell Telegram request succeeded
            # ---------------------------------------------

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "ok": True
                }).encode("utf-8")
            )


        # -------------------------------------------------
        # ERROR HANDLING
        # -------------------------------------------------

        except Exception as error:

            print(
                "Webhook Error:",
                error
            )

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