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
INTERNAL_PROCESS_SECRET = os.environ.get("INTERNAL_PROCESS_SECRET")

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

Your answers must be clean, readable, accurate, and optimized
specifically for Telegram.

FORMATTING:

- Start directly with the answer.
- Use **bold section headings** when useful.
- Keep paragraphs short.
- Leave one blank line between sections.
- Use "- " for bullet lists.
- Use numbered steps for procedures.
- Use **bold** for important terms, but do not overuse it.
- Use emojis sparingly.
- Never generate Markdown tables.
- Convert tables into readable bullet-point comparisons.

CODE:

- Put programming code inside triple-backtick code blocks.
- Mention the programming language when appropriate.
- Explain code separately from the code block.
- If asked to debug code, identify the problem and provide corrected
  code when possible.

IMAGE ANALYSIS:

- Carefully inspect only the supplied image.
- Explain important visible information.
- Read visible text when possible.
- Explain screenshots, diagrams, errors, objects, or scenes.
- If an error is visible, explain it and suggest possible fixes.
- Never claim to see information that cannot be determined.

DOCUMENT ANALYSIS:

- Analyze only the document supplied in the current request.
- Never describe a previously supplied document.
- Follow the user's current caption or instruction.
- If no instruction is provided, summarize the important contents.
- For source-code files, explain the code and identify errors when useful.
- Do not invent content that is not present in the current file.

ACCURACY:

- Do not invent facts.
- If information is uncertain, clearly say so.
- Do not add irrelevant information.
"""


# =========================================================
# TELEGRAM API
# =========================================================

def telegram_request(method, payload=None):

    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    if payload is None:
        request = urllib.request.Request(url)

    else:
        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json"
            }
        )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


# =========================================================
# SEND TELEGRAM MESSAGE
# =========================================================

def send_telegram_message(chat_id, text):

    if not text:
        text = "I couldn't generate a response."

    # Telegram sendMessage has a 4096-character text limit.
    max_length = 3900

    chunks = [
        text[i:i + max_length]
        for i in range(
            0,
            len(text),
            max_length
        )
    ]

    for chunk in chunks:

        try:
            telegram_request(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown"
                }
            )

        except Exception as markdown_error:

            print(
                "Markdown send failed:",
                repr(markdown_error)
            )

            telegram_request(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk
                }
            )


# =========================================================
# TYPING INDICATOR
# =========================================================

def send_typing_action(chat_id):

    try:
        telegram_request(
            "sendChatAction",
            {
                "chat_id": chat_id,
                "action": "typing"
            }
        )

    except Exception as error:
        print(
            "Typing indicator failed:",
            repr(error)
        )


# =========================================================
# DOWNLOAD TELEGRAM FILE
# =========================================================

def get_telegram_file(file_id):

    result = telegram_request(
        f"getFile?file_id={file_id}"
    )

    if not result.get("ok"):
        raise RuntimeError(
            "Telegram could not retrieve the file."
        )

    file_path = result["result"]["file_path"]

    download_url = (
        "https://api.telegram.org/file/"
        f"bot{TELEGRAM_TOKEN}/{file_path}"
    )

    with urllib.request.urlopen(
        download_url,
        timeout=60
    ) as response:

        file_data = response.read()

    return file_data, file_path


# =========================================================
# TEXT MODEL
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
# IMAGE MODEL
# =========================================================

def analyze_image(
    image_data,
    file_name,
    prompt,
    mime_type=None
):

    encoded_image = base64.b64encode(
        image_data
    ).decode("utf-8")

    lower_name = file_name.lower()

    if (
        not mime_type
        or not mime_type.startswith("image/")
    ):

        if lower_name.endswith(".png"):
            mime_type = "image/png"

        elif lower_name.endswith(".webp"):
            mime_type = "image/webp"

        elif lower_name.endswith(".gif"):
            mime_type = "image/gif"

        else:
            mime_type = "image/jpeg"

    image_data_url = (
        f"data:{mime_type};base64,"
        f"{encoded_image}"
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
# PDF MODEL
# =========================================================

def analyze_pdf(
    file_data,
    file_name,
    prompt
):

    encoded_file = base64.b64encode(
        file_data
    ).decode("utf-8")

    pdf_data_url = (
        "data:application/pdf;base64,"
        f"{encoded_file}"
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
# TEXT / CODE FILE
# =========================================================

def analyze_text_file(
    file_data,
    file_name,
    prompt
):

    max_file_size = 1_000_000

    if len(file_data) > max_file_size:

        return (
            "**File too large**\n\n"
            "Please upload a text or code file "
            "smaller than 1 MB."
        )

    try:
        file_text = file_data.decode("utf-8")

    except UnicodeDecodeError:

        file_text = file_data.decode(
            "utf-8",
            errors="replace"
        )

    max_characters = 50_000

    if len(file_text) > max_characters:

        file_text = (
            file_text[:max_characters]
            + "\n\n"
            "[File truncated because it was too long.]"
        )

    user_content = (
        f"{prompt}\n\n"
        f"CURRENT FILE NAME: {file_name}\n\n"
        "CURRENT FILE CONTENT:\n"
        "--------------------\n"
        f"{file_text}"
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
# PROCESS TELEGRAM UPDATE
# =========================================================

def process_update(update):

    update_id = update.get("update_id")

    print(
        f"Processor handling update_id={update_id}"
    )

    message = update.get("message")

    if not message:
        return {
            "ok": True,
            "ignored": True
        }

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return {
            "ok": True,
            "ignored": True
        }

    user_message = message.get("text")

    photos = message.get(
        "photo",
        []
    )

    document = message.get("document")

    caption = message.get(
        "caption",
        ""
    )


    # =====================================================
    # /START
    # =====================================================

    if user_message == "/start":

        reply = (
            "Hello!\n\n"
            "I am your AI assistant powered by OpenRouter.\n\n"
            "You can send me:\n"
            "- Text questions\n"
            "- Images\n"
            "- Images sent as files\n"
            "- PDFs\n"
            "- Text and code files"
        )

        send_telegram_message(
            chat_id,
            reply
        )

        return {
            "ok": True,
            "type": "start"
        }


    # =====================================================
    # PHOTO
    # =====================================================

    if photos:

        send_typing_action(chat_id)

        photo = photos[-1]

        file_id = photo.get("file_id")

        if not file_id:
            raise RuntimeError(
                "Telegram photo has no file_id."
            )

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
            image_data=image_data,
            file_name=file_path,
            prompt=image_prompt
        )

        send_telegram_message(
            chat_id,
            reply
        )

        return {
            "ok": True,
            "type": "photo"
        }


    # =====================================================
    # DOCUMENT
    # =====================================================

    if document:

        send_typing_action(chat_id)

        file_id = document.get("file_id")

        if not file_id:
            raise RuntimeError(
                "Telegram document has no file_id."
            )

        file_name = document.get(
            "file_name",
            "document"
        )

        mime_type = document.get(
            "mime_type",
            "application/octet-stream"
        )

        file_size = document.get(
            "file_size",
            0
        )

        max_download_size = (
            10 * 1024 * 1024
        )

        if (
            file_size
            and file_size > max_download_size
        ):

            send_telegram_message(
                chat_id,
                (
                    "**File too large**\n\n"
                    "Please upload a file smaller "
                    "than 10 MB."
                )
            )

            return {
                "ok": True,
                "type": "file_too_large"
            }

        file_data, file_path = (
            get_telegram_file(file_id)
        )

        document_prompt = (
            caption
            or
            "Analyze this file carefully and explain "
            "its important contents."
        )

        lower_name = file_name.lower()


        # -------------------------------------------------
        # IMAGE SENT AS FILE
        # -------------------------------------------------

        if (
            mime_type.startswith("image/")
            or lower_name.endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".gif"
                )
            )
        ):

            image_prompt = (
                caption
                or
                "Describe and explain what is shown "
                "in this image."
            )

            reply = analyze_image(
                image_data=file_data,
                file_name=file_name,
                prompt=image_prompt,
                mime_type=mime_type
            )


        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        elif (
            mime_type == "application/pdf"
            or lower_name.endswith(".pdf")
        ):

            reply = analyze_pdf(
                file_data=file_data,
                file_name=file_name,
                prompt=document_prompt
            )


        # -------------------------------------------------
        # TEXT / CODE
        # -------------------------------------------------

        elif lower_name.endswith(
            (
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
        ):

            reply = analyze_text_file(
                file_data=file_data,
                file_name=file_name,
                prompt=document_prompt
            )


        # -------------------------------------------------
        # UNSUPPORTED FILE
        # -------------------------------------------------

        else:

            reply = (
                "**Unsupported file type**\n\n"
                "Currently I can analyze:\n"
                "- JPG / JPEG / PNG / WEBP\n"
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

        send_telegram_message(
            chat_id,
            reply
        )

        return {
            "ok": True,
            "type": "document"
        }


    # =====================================================
    # TEXT
    # =====================================================

    if user_message:

        send_typing_action(chat_id)

        reply = ask_text_model(
            user_message
        )

        send_telegram_message(
            chat_id,
            reply
        )

        return {
            "ok": True,
            "type": "text"
        }


    # =====================================================
    # UNSUPPORTED MESSAGE
    # =====================================================

    send_telegram_message(
        chat_id,
        (
            "I currently support text, images, PDFs, "
            "and common text/code files."
        )
    )

    return {
        "ok": True,
        "type": "unsupported"
    }


# =========================================================
# VERCEL PROCESS ENDPOINT
# =========================================================

class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_json_response(
            200,
            {
                "status": "Processor is running"
            }
        )


    def do_POST(self):

        try:

            # ---------------------------------------------
            # VERIFY INTERNAL REQUEST
            # ---------------------------------------------

            received_secret = self.headers.get(
                "X-Internal-Secret"
            )

            if (
                not INTERNAL_PROCESS_SECRET
                or received_secret != INTERNAL_PROCESS_SECRET
            ):

                print(
                    "Rejected unauthorized processor request."
                )

                self.send_json_response(
                    401,
                    {
                        "ok": False,
                        "error": "Unauthorized"
                    }
                )

                return


            # ---------------------------------------------
            # READ UPDATE
            # ---------------------------------------------

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            if content_length <= 0:

                self.send_json_response(
                    400,
                    {
                        "ok": False,
                        "error": "Empty request body"
                    }
                )

                return

            body = self.rfile.read(
                content_length
            )

            update = json.loads(
                body.decode("utf-8")
            )


            # ---------------------------------------------
            # PROCESS
            # ---------------------------------------------

            result = process_update(
                update
            )

            self.send_json_response(
                200,
                result
            )


        except Exception as error:

            print(
                "Processor Error:",
                repr(error)
            )

            self.send_json_response(
                500,
                {
                    "ok": False,
                    "error": str(error)
                }
            )


    # =====================================================
    # JSON RESPONSE
    # =====================================================

    def send_json_response(
        self,
        status_code,
        data
    ):

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.end_headers()

        self.wfile.write(
            json.dumps(data).encode("utf-8")
        )