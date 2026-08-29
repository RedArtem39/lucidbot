# LucidBot — Open-Source AI Roleplay & Companion Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2ba0f5.svg)](https://github.com/aiogram/aiogram)
[![License](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Forge](https://img.shields.io/badge/Stable_Diffusion-Forge-orange.svg)](https://github.com/lllyasviel/stable-diffusion-webui-forge)

**LucidBot** is an interactive AI companion and roleplay platform built on Telegram (`aiogram 3`), OpenRouter LLMs (`DeepSeek V4 Flash / Gemini Flash Lite`), and local **Stable Diffusion Forge** for instant dynamic photo rendering based on the ongoing scene context.

---

## ✨ Features

- **🎭 Rich Character Catalog:**
  - **18+ / Mature Romance:** *Yor Forger, Reze, Makima, 2B, Lucy (Cyberpunk), Raiden Shogun, Tsunade, Asuka, Liya (Succubus), Victoria (CEO), Akane (Yandere), Mitsuha, Evelyn (Dark Elf)*.
  - **SFW Companions:** *Elena (Roommate), Sofia (Psychologist), Max (Gamer Bro), Nova (Sci-Fi Geek)*.
- **💬 Dynamic Context Memory:** SQLite database with full conversation history and affection levels.
- **📸 Real-time Visual Rendering (Selfies):** LLM translates the ongoing dialogue context into Danbooru prompt tags and requests local SDXL Forge (`127.0.0.1:7860`) for instant photo delivery.
- **⚡ Energy & Limits System:** Daily message/photo quotas with hidden promo code activation (`/promo`).
- **🛡️ Multi-Model Resilience:** Primary model routing (`DeepSeek V4 Flash`) with automatic fallback to `Gemini 3.5 Flash Lite`.

---

## 🚀 Quick Start & Installation

### 1. Requirements
- **Python 3.10+** installed and added to `PATH`.
- **Telegram Bot Token** from [@BotFather](https://t.me/BotFather).
- **OpenRouter API Key** from [OpenRouter.ai](https://openrouter.ai).
- *(Optional for Photos)* **Stable Diffusion Forge** running locally with `--api` on `http://127.0.0.1:7860` (recommended model: *AutismMix SDXL / Pony*).

---

### 2. Guided Setup Wizard (Recommended)

Run the interactive setup wizard:

**On Windows:**
Double-click `setup.bat` or run:
```powershell
python setup.py
```

The installer will:
1. Detect your GPU architecture (NVIDIA / AMD / Intel) and suggest optimal Forge flags.
2. Create a virtual environment (`venv`) and install dependencies.
3. Configure `.env` with your API keys.
4. Launch the bot.

---

### 3. Manual Setup

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-username/lucidbot.git
   cd lucidbot
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux / macOS
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure `.env`:**
   ```bash
   cp .env.example .env
   ```
   Fill in your tokens:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENROUTER_API_KEY=your_openrouter_api_key
   FORGE_API_URL=http://127.0.0.1:7860
   ```


5. **Start Bot:**
   ```bash
   python main.py
   ```

---

## ⚙️ Hardware Recommendations for Forge

| GPU Architecture | Recommended Flags |
| :--- | :--- |
| **RTX 40 / 50 Series (Ada / Blackwell)** | `--api --cors-allow-origins=* --opt-channelslast --pin-shared-memory --cuda-stream` |
| **RTX 20 / 30 Series (Turing / Ampere)** | `--api --cors-allow-origins=* --opt-channelslast --attention-split` |
| **AMD Radeon** | `--api --cors-allow-origins=* --directml` |

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See [LICENSE](LICENSE) for details.
