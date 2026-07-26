# 🤖 Hardhik's Personal Assistant — Telegram AI Bot

A multimodal AI-powered Telegram bot built using **Google Gemini**, **Python**, **JavaScript**, and **Vercel**.

The bot can answer normal questions, understand images, summarize PDF documents, and analyze programming/text files directly inside Telegram.

---

## ✨ Features

- 💬 AI text chat
- 🖼️ Image understanding and analysis
- 📄 PDF summarization and analysis
- 💻 Source-code explanation and error detection
- 📁 Text/file analysis
- ⚡ Serverless deployment using Vercel
- 🔐 API keys stored securely as environment variables
- 🤖 Powered by Google Gemini

### Supported File Types

The bot currently supports:

- PDF
- JPG / JPEG
- PNG
- WEBP
- GIF
- TXT
- Markdown
- Python
- C
- C++
- Java
- JavaScript
- TypeScript
- HTML
- CSS
- JSON
- CSV
- XML
- YAML
- SQL

---

# 🏗️ Architecture

```text
User
  ↓
Telegram
  ↓
Telegram Webhook
  ↓
api/webhook.js
  ↓
api/process.py
  ↓
Google Gemini API
  ↓
Gemini response
  ↓
Telegram Bot
  ↓
User
```

The JavaScript webhook receives Telegram updates and forwards them to the Python AI processor.

The Python processor handles:

- Text
- Images
- PDFs
- Programming files
- Other supported text files

---

# 🧠 AI Model

The project currently uses:

```text
gemini-3.1-flash-lite
```

The Gemini API is accessed using Google's official Python SDK:

```text
google-genai
```

---

# 📂 Project Structure

```text
Telegram-AI-BOT/
│
├── api/
│   ├── webhook.js
│   └── process.py
│
├── .gitignore
├── package.json
├── package-lock.json
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

# 1️⃣ Requirements

Install the following before starting:

- Python 3.12+
- Node.js
- npm
- Git
- VS Code
- Telegram account
- Google account
- GitHub account
- Vercel account

Check Python:

```powershell
python --version
```

Check Node.js:

```powershell
node --version
```

Check npm:

```powershell
npm --version
```

Check Git:

```powershell
git --version
```

---

# 2️⃣ Create a Telegram Bot

Open Telegram and search for:

```text
@BotFather
```

Send:

```text
/newbot
```

BotFather will ask for:

1. Bot name
2. Bot username

The username must normally end with:

```text
bot
```

Example:

```text
HardhikPersonalAssistantBot
```

After creating the bot, BotFather gives you a:

```text
BOT TOKEN
```

⚠️ Never publish this token on GitHub.

---

# 3️⃣ Clone the Project

Clone the repository:

```powershell
git clone <YOUR-GITHUB-REPOSITORY-URL>
```

Enter the project:

```powershell
cd "Telegram AI Bot"
```

---

# 4️⃣ Create Python Virtual Environment

Create:

```powershell
python -m venv venv
```

Activate it in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, you should see:

```text
(venv)
```

before your terminal path.

---

# 5️⃣ Install Python Dependencies

Install:

```powershell
pip install -r requirements.txt
```

The project requires:

```text
google-genai
```

Verify:

```powershell
python -c "from google import genai; print('Google GenAI SDK working')"
```

Expected:

```text
Google GenAI SDK working
```

---

# 6️⃣ Install Node Dependencies

Run:

```powershell
npm install
```

The project uses Vercel's Node.js functions for the Telegram webhook.

---

# 7️⃣ Get Gemini API Key

Go to Google AI Studio.

Create a Gemini API key.

Never place the API key directly inside:

```text
process.py
```

or any public GitHub file.

The project reads the key from:

```text
GEMINI_API_KEY
```

---

# 8️⃣ Environment Variables

The project requires these environment variables:

```text
TELEGRAM_BOT_TOKEN
GEMINI_API_KEY
INTERNAL_PROCESS_SECRET
```

### TELEGRAM_BOT_TOKEN

Your token received from BotFather.

### GEMINI_API_KEY

Your API key created using Google AI Studio.

### INTERNAL_PROCESS_SECRET

A random private value used to protect communication between the webhook and processor.

Example:

```text
your-long-random-secret
```

Use a strong random value in production.

---

# 9️⃣ Vercel Environment Variables

After importing the GitHub repository into Vercel:

Go to:

```text
Project
→ Settings
→ Environments
→ Production
→ Environment Variables
```

Add:

```text
TELEGRAM_BOT_TOKEN
```

Then:

```text
GEMINI_API_KEY
```

Then:

```text
INTERNAL_PROCESS_SECRET
```

Store API keys as sensitive values.

After adding or changing environment variables, redeploy the project.

---

# 🔟 Python Configuration

`pyproject.toml` should include the Gemini dependency:

```toml
[project]
name = "telegram-ai-bot"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = [
    "google-genai"
]

[tool.vercel]
entrypoint = "api.process:handler"
```

The important dependency is:

```text
google-genai
```

If this is missing, Vercel may report:

```text
ModuleNotFoundError: No module named 'google'
```

---

# 1️⃣1️⃣ Test the Code Locally

Check Python syntax:

```powershell
python -m py_compile api/process.py
```

No output normally means the syntax check succeeded.

Check JavaScript:

```powershell
node --check api/webhook.js
```

Verify Gemini imports:

```powershell
python -c "from google import genai; from google.genai import types; print('Gemini imports OK')"
```

Expected:

```text
Gemini imports OK
```

---

# 1️⃣2️⃣ Push to GitHub

Check files:

```powershell
git status
```

Stage:

```powershell
git add .
```

Commit:

```powershell
git commit -m "Setup Telegram Gemini AI bot"
```

Push:

```powershell
git push
```

Vercel should automatically create a new deployment when connected to the GitHub repository.

---

# 1️⃣3️⃣ Verify Vercel Deployment

After deployment becomes:

```text
Ready
```

open:

```text
https://YOUR-VERCEL-DOMAIN.vercel.app/api/process
```

A working processor should return something similar to:

```json
{
  "status": "Gemini processor is running",
  "model": "gemini-3.1-flash-lite"
}
```

---

# 1️⃣4️⃣ Configure Telegram Webhook

Your Telegram webhook should point to:

```text
https://YOUR-VERCEL-DOMAIN.vercel.app/api/webhook
```

Configure the webhook using Telegram's Bot API.

The webhook URL must use HTTPS.

After configuration, Telegram sends new bot updates to the Vercel webhook.

---

# 1️⃣5️⃣ Check Webhook Status

Use Telegram's:

```text
getWebhookInfo
```

A healthy configuration should show your Vercel webhook URL.

Check:

```text
pending_update_count
```

and:

```text
last_error_message
```

when troubleshooting.

---

# 🧪 Testing

Test features individually.

## Test 1 — Text

Send:

```text
What is Python?
```

Expected:

```text
AI-generated explanation
```

---

## Test 2 — Image

Upload an image with:

```text
Describe this image in detail.
```

The bot should analyze the image.

---

## Test 3 — PDF

Upload a PDF with:

```text
Summarize this PDF and give me the key points.
```

The bot should analyze the current PDF.

---

## Test 4 — Python File

Upload:

```text
example.py
```

with:

```text
Explain this code and find any errors.
```

The bot should explain the source code and identify potential problems.

---

# 🔐 Security

Never commit:

```text
Telegram bot tokens
Gemini API keys
Internal secrets
.env files
```

Recommended `.gitignore`:

```gitignore
.env
.env.local
venv/
__pycache__/
*.pyc
node_modules/
process_backup.py
```

If an API key or bot token is accidentally published, revoke it and create a new one.

---

# 🛠️ Common Errors

## No module named 'google'

Error:

```text
ModuleNotFoundError: No module named 'google'
```

Check that `google-genai` exists in your dependencies.

Run locally:

```powershell
pip install google-genai
```

Also verify `pyproject.toml`.

---

## Gemini API key missing

Error:

```text
No API key was provided
```

or:

```text
GEMINI_API_KEY is missing
```

Check Vercel:

```text
Settings
→ Environments
→ Production
→ Environment Variables
```

Make sure:

```text
GEMINI_API_KEY
```

contains the actual API key in the **Value** field.

Redeploy after changing it.

---

## Telegram Bot Doesn't Reply

Check:

1. Vercel deployment is Ready.
2. `/api/process` works.
3. Telegram webhook URL is correct.
4. `TELEGRAM_BOT_TOKEN` exists.
5. `INTERNAL_PROCESS_SECRET` exists.
6. Gemini API quota has not been exceeded.
7. Vercel function logs for `/api/webhook`.
8. Vercel function logs for `/api/process`.

---

## Gemini Rate Limit

If Gemini returns:

```text
429
```

the project may have reached a request, token, or quota limit.

Check the Google AI Studio usage/rate-limit dashboard.

---

# 🚀 Current Capabilities

| Feature | Status |
|---|---|
| AI Text Chat | ✅ Working |
| Image Analysis | ✅ Working |
| PDF Analysis | ✅ Working |
| Python File Analysis | ✅ Working |
| Code File Analysis | ✅ Working |
| Gemini Integration | ✅ Working |
| Vercel Hosting | ✅ Working |
| Telegram Webhook | ✅ Working |
| AI Image Generation | 🚧 Planned |
| PDF Generation | 🚧 Planned |
| PowerPoint Generation | 🚧 Planned |
| Word Generation | 🚧 Planned |
| Excel Generation | 🚧 Planned |

---

# 🔮 Planned Features

Future versions may include:

- 🎨 AI image generation
- 📄 PDF creation
- 📊 PowerPoint creation
- 📝 Word document creation
- 📈 Excel spreadsheet creation
- 🧠 Conversation memory
- 👤 User-specific chat history
- 📊 Usage tracking
- ⚙️ Telegram commands
- 🔄 Multiple Gemini models
- 🛡️ Improved rate limiting

---

# 🧰 Technology Stack

### Backend

- Python
- JavaScript

### AI

- Google Gemini
- Google GenAI Python SDK

### Platform

- Telegram Bot API

### Hosting

- Vercel Serverless Functions

### Development

- Visual Studio Code
- Git
- GitHub

---

# 📌 Important

A Google Gemini consumer subscription and the Gemini API are separate products.

This project uses the **Gemini API through an API key**.

API availability, quotas, rate limits, and pricing depend on the Google AI project/model being used.

---

# 👨‍💻 Author

**Hardhik Sai**

Built as a Telegram-based multimodal AI assistant project.

---

# ⭐ Support

If you find this project useful, consider starring the GitHub repository.

Contributions and improvements are welcome.
