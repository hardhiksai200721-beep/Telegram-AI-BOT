import os
import json
import urllib.request
import re
import uuid
import tempfile
from xml.sax.saxutils import escape

from http.server import BaseHTTPRequestHandler
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


# =========================================================
# CONFIGURATION
# =========================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
INTERNAL_PROCESS_SECRET = os.environ.get("INTERNAL_PROCESS_SECRET")

MODEL = "gemini-3.1-flash-lite"

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is missing.")


def get_gemini_client():
    """Create the Gemini client only when an AI request is actually made."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Set it in your environment or Vercel Environment Variables."
        )

    return genai.Client(api_key=GEMINI_API_KEY)


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
# GEMINI CONFIGURATION
# =========================================================

def gemini_config():
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=1000,
    )


def get_response_text(response):
    text = getattr(response, "text", None)

    if text:
        return text.strip()

    return (
        "I couldn't generate a text response for this request. "
        "Please try again."
    )



# =========================================================
# PDF GENERATION
# =========================================================

def is_pdf_generation_request(text):
    if not text:
        return False

    lower = text.lower().strip()

    return (
        "pdf" in lower
        and any(
            word in lower
            for word in (
                "create",
                "generate",
                "make",
                "prepare",
                "build",
                "give me",
            )
        )
    )


def clean_pdf_topic(user_message):
    topic = user_message.strip()

    patterns = [
        r"(?i)\bcreate\s+(?:a\s+)?pdf(?:\s+file|\s+document)?\s*(?:about|on|for)?\s*",
        r"(?i)\bgenerate\s+(?:a\s+)?pdf(?:\s+file|\s+document)?\s*(?:about|on|for)?\s*",
        r"(?i)\bmake\s+(?:me\s+)?(?:a\s+)?pdf(?:\s+file|\s+document)?\s*(?:about|on|for)?\s*",
        r"(?i)\bprepare\s+(?:a\s+)?pdf(?:\s+file|\s+document)?\s*(?:about|on|for)?\s*",
        r"(?i)\bgive\s+me\s+(?:a\s+)?pdf(?:\s+file|\s+document)?\s*(?:about|on|for)?\s*",
    ]

    for pattern in patterns:
        topic = re.sub(pattern, "", topic).strip()

    return topic or "Requested Topic"


def generate_pdf_content(user_message):
    prompt = f"""
Create high-quality content for a PDF requested by the user.

USER REQUEST:
{user_message}

Requirements:
- Start with a clear title using "# ".
- Give a short introduction.
- Organize the content into logical sections using "## ".
- Use clear explanations.
- Use "- " for bullet points where useful.
- Include examples when appropriate.
- Do not say that you cannot create a PDF.
- Do not provide manual PDF-conversion instructions.
- Do not use Markdown tables.
- Return only the content that belongs inside the PDF.
"""

    response = get_gemini_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=3000,
        ),
    )

    return get_response_text(response)


def make_safe_filename(topic):
    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        topic,
    ).strip("_")[:60]

    if not safe_name:
        safe_name = "generated_document"

    return f"{safe_name}.pdf"


def create_pdf_file(content, topic):
    filename = make_safe_filename(topic)

    file_path = os.path.join(
        tempfile.gettempdir(),
        f"{uuid.uuid4().hex}_{filename}",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=24,
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        spaceAfter=8,
    )

    bullet_style = ParagraphStyle(
        "CustomBullet",
        parent=body_style,
        leftIndent=18,
        firstLineIndent=-8,
    )

    document = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=topic,
        author="Hardhik's Personal Assistant",
    )

    story = []
    first_added = False
    in_code_block = False

    for raw_line in content.splitlines():
        line = raw_line.strip()

        if line.startswith("```"):
            in_code_block = not in_code_block
            continue

        if not line:
            story.append(Spacer(1, 6))
            continue

        safe_line = escape(line)
        safe_line = safe_line.replace("**", "").replace("__", "")

        if in_code_block:
            story.append(
                Paragraph(
                    f'<font name="Courier">{safe_line}</font>',
                    body_style,
                )
            )

        elif safe_line.startswith("# "):
            story.append(
                Paragraph(
                    safe_line[2:].strip(),
                    title_style,
                )
            )

        elif safe_line.startswith("## "):
            story.append(
                Paragraph(
                    safe_line[3:].strip(),
                    heading_style,
                )
            )

        elif safe_line.startswith("### "):
            story.append(
                Paragraph(
                    safe_line[4:].strip(),
                    heading_style,
                )
            )

        elif safe_line.startswith(("- ", "* ")):
            story.append(
                Paragraph(
                    f"&#8226; {safe_line[2:].strip()}",
                    bullet_style,
                )
            )

        else:
            story.append(
                Paragraph(
                    safe_line,
                    body_style if first_added else title_style,
                )
            )

        first_added = True

    if not story:
        story.append(
            Paragraph(
                escape(topic),
                title_style,
            )
        )

    document.build(story)

    return file_path, filename


# =========================================================
# TELEGRAM API
# =========================================================

def telegram_request(method, payload=None):

    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"

    if payload is None:
        request = urllib.request.Request(url)

    else:
        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


# =========================================================
# TELEGRAM MESSAGE
# =========================================================

def send_telegram_message(chat_id, text):

    if not text:
        text = "I couldn't generate a response."

    # Stay below Telegram's message-length limit.
    max_length = 3900

    chunks = [
        text[i:i + max_length]
        for i in range(0, len(text), max_length)
    ]

    for chunk in chunks:

        try:
            telegram_request(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                },
            )

        except Exception as markdown_error:
            print("Markdown send failed:", repr(markdown_error))

            telegram_request(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                },
            )


def send_typing_action(chat_id):

    try:
        telegram_request(
            "sendChatAction",
            {
                "chat_id": chat_id,
                "action": "typing",
            },
        )

    except Exception as error:
        print("Typing indicator failed:", repr(error))



# =========================================================
# TELEGRAM DOCUMENT UPLOAD
# =========================================================

def send_telegram_document(
    chat_id,
    file_path,
    filename,
    caption=None,
):
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

    boundary = "----TelegramBotBoundary" + uuid.uuid4().hex
    body = bytearray()

    def add_field(name, value):
        body.extend(
            f"--{boundary}\r\n".encode("utf-8")
        )
        body.extend(
            (
                f'Content-Disposition: form-data; '
                f'name="{name}"\r\n\r\n'
            ).encode("utf-8")
        )
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    add_field("chat_id", chat_id)

    if caption:
        add_field("caption", caption)

    with open(file_path, "rb") as pdf_file:
        file_data = pdf_file.read()

    body.extend(
        f"--{boundary}\r\n".encode("utf-8")
    )
    body.extend(
        (
            'Content-Disposition: form-data; '
            f'name="document"; filename="{filename}"\r\n'
        ).encode("utf-8")
    )
    body.extend(
        b"Content-Type: application/pdf\r\n\r\n"
    )
    body.extend(file_data)
    body.extend(b"\r\n")
    body.extend(
        f"--{boundary}--\r\n".encode("utf-8")
    )

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendDocument"
    )

    request = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": (
                f"multipart/form-data; boundary={boundary}"
            )
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            "Telegram could not send the PDF."
        )

    return result


# =========================================================
# DOWNLOAD TELEGRAM FILE
# =========================================================

def get_telegram_file(file_id):

    result = telegram_request(
        f"getFile?file_id={file_id}"
    )

    if not result.get("ok"):
        raise RuntimeError("Telegram could not retrieve the file.")

    file_path = result["result"]["file_path"]

    download_url = (
        f"https://api.telegram.org/file/"
        f"bot{TELEGRAM_TOKEN}/{file_path}"
    )

    with urllib.request.urlopen(download_url, timeout=60) as response:
        file_data = response.read()

    return file_data, file_path


# =========================================================
# GEMINI TEXT
# =========================================================

def ask_text_model(user_message):

    response = get_gemini_client().models.generate_content(
        model=MODEL,
        contents=user_message,
        config=gemini_config(),
    )

    return get_response_text(response)


# =========================================================
# GEMINI IMAGE
# =========================================================

def analyze_image(
    image_data,
    file_name,
    prompt,
    mime_type=None,
):

    lower_name = file_name.lower()

    if not mime_type or not mime_type.startswith("image/"):

        if lower_name.endswith(".png"):
            mime_type = "image/png"

        elif lower_name.endswith(".webp"):
            mime_type = "image/webp"

        elif lower_name.endswith(".gif"):
            mime_type = "image/gif"

        else:
            mime_type = "image/jpeg"

    image_part = types.Part.from_bytes(
        data=image_data,
        mime_type=mime_type,
    )

    response = get_gemini_client().models.generate_content(
        model=MODEL,
        contents=[
            prompt,
            image_part,
        ],
        config=gemini_config(),
    )

    return get_response_text(response)


# =========================================================
# GEMINI PDF
# =========================================================

def analyze_pdf(
    file_data,
    file_name,
    prompt,
):

    pdf_part = types.Part.from_bytes(
        data=file_data,
        mime_type="application/pdf",
    )

    full_prompt = (
        f"{prompt}\n\n"
        f"Document name: {file_name}"
    )

    response = get_gemini_client().models.generate_content(
        model=MODEL,
        contents=[
            full_prompt,
            pdf_part,
        ],
        config=gemini_config(),
    )

    return get_response_text(response)


# =========================================================
# GEMINI TEXT / CODE FILE
# =========================================================

def analyze_text_file(
    file_data,
    file_name,
    prompt,
):

    max_file_size = 1_000_000

    if len(file_data) > max_file_size:
        return (
            "**File too large**\n\n"
            "Please upload a text or code file smaller than 1 MB."
        )

    try:
        file_text = file_data.decode("utf-8")

    except UnicodeDecodeError:
        file_text = file_data.decode(
            "utf-8",
            errors="replace",
        )

    max_characters = 50_000

    if len(file_text) > max_characters:
        file_text = (
            file_text[:max_characters]
            + "\n\n[File truncated because it was too long.]"
        )

    user_content = (
        f"{prompt}\n\n"
        f"CURRENT FILE NAME: {file_name}\n\n"
        "CURRENT FILE CONTENT:\n"
        "--------------------\n"
        f"{file_text}"
    )

    response = get_gemini_client().models.generate_content(
        model=MODEL,
        contents=user_content,
        config=gemini_config(),
    )

    return get_response_text(response)


# =========================================================
# FRIENDLY GEMINI ERROR
# =========================================================

def send_ai_error(chat_id, error):

    error_text = str(error)
    lower_error = error_text.lower()

    print("Gemini API Error:", repr(error))

    if (
        "429" in error_text
        or "resource_exhausted" in lower_error
        or "quota" in lower_error
        or "rate limit" in lower_error
    ):
        message = (
            "**Gemini usage limit reached**\n\n"
            "The AI service has temporarily reached its request "
            "or quota limit. Please try again later."
        )

    elif (
        "api key" in lower_error
        or "api_key" in lower_error
        or "unauthenticated" in lower_error
        or "permission_denied" in lower_error
    ):
        message = (
            "**Gemini API authentication error**\n\n"
            "The bot could not authenticate with Google Gemini. "
            "The API configuration needs to be checked."
        )

    else:
        message = (
            "**AI request failed**\n\n"
            "I couldn't process that request right now. "
            "Please try again shortly."
        )

    try:
        send_telegram_message(chat_id, message)

    except Exception as telegram_error:
        print(
            "Could not send AI error to Telegram:",
            repr(telegram_error),
        )


# =========================================================
# PROCESS TELEGRAM UPDATE
# =========================================================

def process_update(update):

    update_id = update.get("update_id")

    print(f"Processor handling update_id={update_id}")

    message = update.get("message")

    if not message:
        return {
            "ok": True,
            "ignored": True,
        }

    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return {
            "ok": True,
            "ignored": True,
        }

    user_message = message.get("text")
    photos = message.get("photo", [])
    document = message.get("document")
    caption = message.get("caption", "")

    # -----------------------------------------------------
    # /START
    # -----------------------------------------------------

    if user_message == "/start":

        send_telegram_message(
            chat_id,
            (
                "Hello!\n\n"
                "I am your Gemini-powered AI assistant.\n\n"
                "You can send me:\n"
                "- Text questions\n"
                "- Images\n"
                "- Images sent as files\n"
                "- PDFs\n"
                "- Text and code files\n"
                "- Generate PDF documents"
            ),
        )

        return {
            "ok": True,
            "type": "start",
        }

    # -----------------------------------------------------
    # PHOTO
    # -----------------------------------------------------

    if photos:

        send_typing_action(chat_id)

        try:
            photo = photos[-1]
            file_id = photo.get("file_id")

            if not file_id:
                raise RuntimeError(
                    "Telegram photo has no file_id."
                )

            image_data, file_path = get_telegram_file(file_id)

            image_prompt = (
                caption
                or "Describe and explain what is shown in this image."
            )

            reply = analyze_image(
                image_data=image_data,
                file_name=file_path,
                prompt=image_prompt,
            )

            send_telegram_message(chat_id, reply)

        except Exception as error:
            send_ai_error(chat_id, error)

        return {
            "ok": True,
            "type": "photo",
        }

    # -----------------------------------------------------
    # DOCUMENT
    # -----------------------------------------------------

    if document:

        send_typing_action(chat_id)

        try:
            file_id = document.get("file_id")

            if not file_id:
                raise RuntimeError(
                    "Telegram document has no file_id."
                )

            file_name = document.get(
                "file_name",
                "document",
            )

            mime_type = document.get(
                "mime_type",
                "application/octet-stream",
            )

            file_size = document.get(
                "file_size",
                0,
            )

            max_download_size = 10 * 1024 * 1024

            if file_size and file_size > max_download_size:

                send_telegram_message(
                    chat_id,
                    (
                        "**File too large**\n\n"
                        "Please upload a file smaller than 10 MB."
                    ),
                )

                return {
                    "ok": True,
                    "type": "file_too_large",
                }

            file_data, _ = get_telegram_file(file_id)

            document_prompt = (
                caption
                or (
                    "Analyze this file carefully and explain "
                    "its important contents."
                )
            )

            lower_name = file_name.lower()

            # IMAGE SENT AS DOCUMENT
            if (
                mime_type.startswith("image/")
                or lower_name.endswith(
                    (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".gif",
                    )
                )
            ):

                reply = analyze_image(
                    image_data=file_data,
                    file_name=file_name,
                    prompt=(
                        caption
                        or (
                            "Describe and explain what is shown "
                            "in this image."
                        )
                    ),
                    mime_type=mime_type,
                )

            # PDF
            elif (
                mime_type == "application/pdf"
                or lower_name.endswith(".pdf")
            ):

                reply = analyze_pdf(
                    file_data=file_data,
                    file_name=file_name,
                    prompt=document_prompt,
                )

            # TEXT / CODE
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
                    ".sql",
                )
            ):

                reply = analyze_text_file(
                    file_data=file_data,
                    file_name=file_name,
                    prompt=document_prompt,
                )

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
                reply,
            )

        except Exception as error:
            send_ai_error(chat_id, error)

        return {
            "ok": True,
            "type": "document",
        }

    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    if user_message:

        send_typing_action(chat_id)

        try:
            # PDF GENERATION
            if is_pdf_generation_request(user_message):
                topic = clean_pdf_topic(user_message)

                send_telegram_message(
                    chat_id,
                    "📄 Creating your PDF. Please wait...",
                )

                pdf_content = generate_pdf_content(
                    user_message
                )

                pdf_path = None

                try:
                    pdf_path, pdf_filename = create_pdf_file(
                        content=pdf_content,
                        topic=topic,
                    )

                    send_telegram_document(
                        chat_id=chat_id,
                        file_path=pdf_path,
                        filename=pdf_filename,
                        caption=(
                            f"📄 {topic}\n\n"
                            "Generated by Hardhik's Personal Assistant"
                        ),
                    )

                finally:
                    if (
                        pdf_path
                        and os.path.exists(pdf_path)
                    ):
                        try:
                            os.remove(pdf_path)
                        except Exception as cleanup_error:
                            print(
                                "PDF cleanup failed:",
                                repr(cleanup_error),
                            )

                return {
                    "ok": True,
                    "type": "generated_pdf",
                }

            # NORMAL AI CHAT
            reply = ask_text_model(user_message)

            send_telegram_message(
                chat_id,
                reply,
            )

        except Exception as error:
            send_ai_error(chat_id, error)

        return {
            "ok": True,
            "type": "text",
        }

    # -----------------------------------------------------
    # UNSUPPORTED
    # -----------------------------------------------------

    send_telegram_message(
        chat_id,
        (
            "I currently support text, images, PDFs, "
            "and common text/code files."
        ),
    )

    return {
        "ok": True,
        "type": "unsupported",
    }


# =========================================================
# VERCEL PROCESS ENDPOINT
# =========================================================

class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_json_response(
            200,
            {
                "status": "Gemini processor is running",
                "model": MODEL,
            },
        )

    def do_POST(self):

        try:
            # Verify request from webhook.js
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
                        "error": "Unauthorized",
                    },
                )

                return

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0,
                )
            )

            if content_length <= 0:

                self.send_json_response(
                    400,
                    {
                        "ok": False,
                        "error": "Empty request body",
                    },
                )

                return

            body = self.rfile.read(content_length)

            update = json.loads(
                body.decode("utf-8")
            )

            result = process_update(update)

            self.send_json_response(
                200,
                result,
            )

        except Exception as error:

            print(
                "Processor Error:",
                repr(error),
            )

            self.send_json_response(
                500,
                {
                    "ok": False,
                    "error": str(error),
                },
            )

    def send_json_response(
        self,
        status_code,
        data,
    ):

        self.send_response(status_code)

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.end_headers()

        self.wfile.write(
            json.dumps(data).encode("utf-8")
        )