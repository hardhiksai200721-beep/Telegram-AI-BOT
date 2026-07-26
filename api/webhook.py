import os
import json
import base64
import urllib.request

from http.server import BaseHTTPRequestHandler
from openai import OpenAI


# =========================================================
# CONFIGURATION
# =========================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MODEL = "google/gemma-4-26b-a4b-it:free"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a helpful AI assistant responding through Telegram.

Your answers must be clean, readable, professional, and optimized
specifically for Telegram.

FORMATTING:

- Start directly with the answer.
- Use **bold section headings** when useful.
- Keep paragraphs short.
- Leave one blank line between sections.
- Use "- " for bullet lists.
- Use "1.", "2.", "3." for numbered steps.
- Use **bold** for important terms, but do not overuse it.
- Use emojis sparingly.
- Never generate Markdown tables.
- Convert tables into readable bullet-point comparisons.

CODE:

- Put programming code inside triple-backtick code blocks.
- Mention the programming language when appropriate.
- Explain code separately from the code block.
- If the user asks to debug code, explain the problem and provide
  corrected code when possible.

TECHNICAL QUESTIONS:

- Give a short explanation first.
- Then explain important concepts using sections or bullet points.
- Include simple examples when useful.

SIMPLE QUESTIONS:

- Give concise answers.
- Do not create unnecessary sections.

IMAGE ANALYSIS:

- Carefully inspect the supplied image.
- Explain important visible information.
- Read visible text when possible.
- Explain screenshots, diagrams, errors, objects, or scenes.
- If an error is visible, explain it and suggest possible fixes.
- Never claim to see information that cannot be determined.

DOCUMENT ANALYSIS:

- Carefully analyze the supplied document or file.
- Follow the user's instruction or caption.
- If no specific instruction is provided, summarize and explain
  the important contents.
- For source-code files, explain the code and identify errors when useful.
- Do not invent content that is not present in the file.

ACCURACY:

- Do not invent facts.
- If information is uncertain, clearly say so.
- Do not add irrelevant information.
"""


# =========================================================
# TELEGRAM - SEND MESSAGE
# =========================================================

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    # Telegram has a message-size limit.
    # Split very long responses into smaller messages.
    max_length = 4000

    if not text:
        text = "I couldn't generate a response."

    chunks = [
        text[i:i + max_length]
        for i in range(0, len(text), max_length)
    ]

    for chunk in chunks:

        # First try Markdown
        data = json.dumps({
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown"
        }).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(request) as response:
                response.read()

        except Exception:

            # If Markdown parsing fails, send plain text
            fallback_data = json.dumps({
                "chat_id": chat_id,
                "text": chunk
            }).encode("utf-8")

            fallback_request = urllib.request.Request(
                url,
                data=fallback_data,
                headers={
                    "Content-Type": "application/json"
                }
            )

            with urllib.request.urlopen(fallback_request) as response:
                response.read()


# =========================================================
# TELEGRAM - TYPING INDICATOR
# =========================================================

def send_typing_action(chat_id):
    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendChatAction"
    )

    data = json.dumps({
        "chat_id": chat_id,
        "action": "typing"
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(request) as response:
            response.read()

    except Exception:
        pass


# =========================================================
# TELEGRAM - DOWNLOAD FILE
# =========================================================

def get_telegram_file(file_id):

    get_file_url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/getFile"
        f"?file_id={file_id}"
    )

    with urllib.request.urlopen(get_file_url) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise Exception("Telegram could not retrieve the file.")

    file_path = result["result"]["file_path"]

    download_url = (
        f"https://api.telegram.org/file/"
        f"bot{TELEGRAM_TOKEN}/{file_path}"
    )

    with urllib.request.urlopen(download_url) as response:
        file_data = response.read()

    return file_data, file_path


# =========================================================
# OPENROUTER - NORMAL TEXT
# =========================================================

def ask_text_model(user_message):

    completion = client.chat.completions.create(
        model=MODEL,
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

    return completion.choices[0].message.content


# =========================================================
# OPENROUTER - IMAGE
# =========================================================

def analyze_image(image_data, file_path, prompt):

    encoded_image = base64.b64encode(
        image_data
    ).decode("utf-8")

    extension = file_path.lower().split(".")[-1]

    if extension == "png":
        mime_type = "image/png"

    elif extension == "webp":
        mime_type = "image/webp"

    else:
        mime_type = "image/jpeg"

    image_data_url = (
        f"data:{mime_type};base64,{encoded_image}"
    )

    completion = client.chat.completions.create(
        model=MODEL,
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
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ]
    )

    return completion.choices[0].message.content


# =========================================================
# OPENROUTER - PDF
# =========================================================

def analyze_pdf(file_data, file_name, prompt):

    encoded_file = base64.b64encode(
        file_data
    ).decode("utf-8")

    pdf_data_url = (
        f"data:application/pdf;base64,{encoded_file}"
    )

    completion = client.chat.completions.create(
        model=MODEL,
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
                        "text": prompt
                    },
                    {
                        "type": "file",
                        "file": {
                            "filename": file_name,
                            "file_data": pdf_data_url
                        }
                    }
                ]
            }
        ]
    )

    return completion.choices[0].message.content


# =========================================================
# OPENROUTER - TEXT / CODE FILE
# =========================================================

def analyze_text_file(file_data, file_name, prompt):

    # Maximum downloaded text/code file size
    max_file_size = 1_000_000

    if len(file_data) > max_file_size:
        return (
            "📄 **File too large**\n\n"
            "Please upload a text or code file smaller than 1 MB."
        )

    try:
        file_text = file_data.decode("utf-8")

    except UnicodeDecodeError:
        file_text = file_data.decode(
            "utf-8",
            errors="replace"
        )

    # Avoid sending extremely large text prompts
    max_characters = 50_000

    truncated = False

    if len(file_text) > max_characters:
        file_text = file_text[:max_characters]
        truncated = True

    user_content = (
        f"{prompt}\n\n"
        f"File name: {file_name}\n\n"
        "FILE CONTENT:\n"
        f"{file_text}"
    )

    if truncated:
        user_content += (
            "\n\n"
            "[The file was truncated because it was too long.]"
        )

    completion = client.chat.completions.create(
        model=MODEL,
        max_tokens=700,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    )

    return completion.choices[0].message.content


# =========================================================
# VERCEL WEBHOOK
# =========================================================

class handler(BaseHTTPRequestHandler):

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.end_headers()

        response = {
            "status": "Telegram AI Bot is running"
        }

        self.wfile.write(
            json.dumps(response).encode("utf-8")
        )


    # -----------------------------------------------------
    # POST
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

            # -------------------------------------------------
            # Detect Telegram message type
            # -------------------------------------------------

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

            # -------------------------------------------------
            # Process message
            # -------------------------------------------------

            if chat_id and (
                user_message
                or photos
                or document
            ):

                # =============================================
                # /START
                # =============================================

                if user_message == "/start":

                    reply = (
                        "Hello! 👋\n\n"
                        "I am your AI assistant powered by "
                        "OpenRouter.\n\n"
                        "You can send me:\n"
                        "- Text questions\n"
                        "- Images\n"
                        "- PDFs\n"
                        "- Text and code files"
                    )


                # =============================================
                # IMAGE
                # =============================================

                elif photos:

                    send_typing_action(chat_id)

                    # Largest Telegram photo version
                    file_id = photos[-1]["file_id"]

                    image_data, file_path = (
                        get_telegram_file(file_id)
                    )

                    image_prompt = (
                        caption
                        or
                        "Describe and explain what is shown "
                        "in this image."
                    )

                    reply = analyze_image(
                        image_data,
                        file_path,
                        image_prompt
                    )


                # =============================================
                # DOCUMENT
                # =============================================

                elif document:

                    send_typing_action(chat_id)

                    file_id = document.get(
                        "file_id"
                    )

                    file_name = document.get(
                        "file_name",
                        "document"
                    )

                    mime_type = document.get(
                        "mime_type",
                        "application/octet-stream"
                    )

                    file_data, file_path = (
                        get_telegram_file(file_id)
                    )

                    document_prompt = (
                        caption
                        or
                        "Analyze this file and explain "
                        "its important contents."
                    )

                    # -----------------------------------------
                    # PDF
                    # -----------------------------------------

                    if (
                        mime_type == "application/pdf"
                        or file_name.lower().endswith(".pdf")
                    ):

                        reply = analyze_pdf(
                            file_data,
                            file_name,
                            document_prompt
                        )


                    # -----------------------------------------
                    # TEXT / CODE FILE
                    # -----------------------------------------

                    else:

                        supported_extensions = (
                            ".txt",
                            ".md",
                            ".py",
                            ".c",
                            ".cpp",
                            ".h",
                            ".hpp",
                            ".java",
                            ".js",
                            ".ts",
                            ".html",
                            ".css",
                            ".json",
                            ".csv",
                            ".xml",
                            ".yaml",
                            ".yml",
                            ".sql"
                        )

                        if file_name.lower().endswith(
                            supported_extensions
                        ):

                            reply = analyze_text_file(
                                file_data,
                                file_name,
                                document_prompt
                            )

                        else:

                            reply = (
                                "📄 **Unsupported file type**\n\n"
                                "Currently I can analyze:\n"
                                "- PDF\n"
                                "- TXT / Markdown\n"
                                "- Python\n"
                                "- C / C++\n"
                                "- Java\n"
                                "- JavaScript / TypeScript\n"
                                "- HTML / CSS\n"
                                "- JSON / CSV\n"
                                "- XML / YAML\n"
                                "- SQL"
                            )


                # =============================================
                # NORMAL TEXT
                # =============================================

                else:

                    send_typing_action(chat_id)

                    reply = ask_text_model(
                        user_message
                    )


                # =============================================
                # SEND RESPONSE
                # =============================================

                send_telegram_message(
                    chat_id,
                    reply
                )


            # -------------------------------------------------
            # Return success to Telegram
            # -------------------------------------------------

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


        # -----------------------------------------------------
        # ERROR
        # -----------------------------------------------------

        except Exception as error:

            print(
                "Webhook Error:",
                repr(error)
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