import os
import sys
import subprocess
import shutil
import platform

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def detect_gpu():
    gpu_info = []
    # Try nvidia-smi
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=3
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().split("\n")
            for l in lines:
                parts = l.split(",")
                name = parts[0].strip()
                vram = parts[1].strip() if len(parts) > 1 else "Unknown"
                gpu_info.append((name, vram))
            return gpu_info
    except Exception:
        pass

    # Windows WMIC fallback
    if platform.system() == "Windows":
        try:
            res = subprocess.run(
                ["powershell", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=4
            )
            if res.returncode == 0 and res.stdout.strip():
                for name in res.stdout.strip().split("\n"):
                    name = name.strip()
                    if name:
                        gpu_info.append((name, "System Memory Managed"))
        except Exception:
            pass

    return gpu_info

def suggest_forge_flags(gpu_name: str):
    gpu_lower = gpu_name.lower()
    flags = ["--api", "--cors-allow-origins=*"]
    
    print("\n[GPU-Оптимизация] Рекомендованные флаги для Stable Diffusion Forge:")
    if "rtx 50" in gpu_lower or "rtx 40" in gpu_lower:
        flags.extend(["--opt-channelslast", "--pin-shared-memory", "--cuda-stream"])
        print("  -> Для вашей архитектуры (RTX 40/50 Series / Ada / Blackwell):")
        print("     Флаги запуска Forge: " + " ".join(flags))
    elif "rtx 30" in gpu_lower or "rtx 20" in gpu_lower or "gtx" in gpu_lower:
        flags.extend(["--opt-channelslast", "--attention-split"])
        print("  -> Для архитектуры Ampere/Turing/Pascal:")
        print("     Флаги запуска Forge: " + " ".join(flags))
    elif "amd" in gpu_lower or "radeon" in gpu_lower:
        flags.extend(["--directml"])
        print("  -> Для AMD Radeon:")
        print("     Флаги запуска Forge: " + " ".join(flags))
    else:
        print("  -> Стандартный запуск Forge: --api --cors-allow-origins=*")
    
    print("  * Убедитесь, что Forge запущен с параметром `--api` на порту 7860.")

def main():
    print_header("LucidBot — Setup & Hardware Detector")
    
    # 1. Python Check
    py_ver = sys.version.split()[0]
    print(f"[*] Python Version: {py_ver} ({sys.executable})")
    if sys.version_info < (3, 10):
        print("[!] Внимание: Рекомендуется Python 3.10+ для стабильной работы aiogram 3.")

    # 2. GPU Detection
    gpus = detect_gpu()
    if gpus:
        print("\n[*] Обнаруженные видеокарты:")
        for name, vram in gpus:
            print(f"  + GPU: {name} (VRAM: {vram})")
        suggest_forge_flags(gpus[0][0])
    else:
        print("\n[*] GPU не определен. Рендеринг может выполняться на CPU или удалённом сервере.")

    # 3. Virtual Environment & Dependencies
    print_header("Установка зависимостей")
    venv_dir = os.path.join(os.path.dirname(__file__), "venv")
    
    choice = input("\n[?] Установить зависимости в виртуальное окружение (venv)? [y/n] (по умолчанию: y): ").strip().lower()
    if choice in ("", "y", "yes", "д", "да"):
        if not os.path.exists(venv_dir):
            print("[*] Создание виртуального окружения (venv)...")
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("[+] Окружение venv успешно создано.")

        # Determine venv python path
        if platform.system() == "Windows":
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
            venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            venv_python = os.path.join(venv_dir, "bin", "python")
            venv_pip = os.path.join(venv_dir, "bin", "pip")

        print("[*] Установка библиотек из requirements.txt...")
        req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
        subprocess.run([venv_pip, "install", "-r", req_file], check=True)
        print("[+] Все зависимости успешно установлены!")
    else:
        print("[*] Установка зависимостей пропущена.")
        venv_python = sys.executable

    # 4. Configuration (.env)
    print_header("Настройка API-ключей (.env)")
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    
    bot_token = ""
    openrouter_key = ""

    if os.path.exists(env_file):
        print("[*] Найден существующий файл .env.")
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    bot_token = line.split("=", 1)[1].strip()
                elif line.startswith("OPENROUTER_API_KEY="):
                    openrouter_key = line.split("=", 1)[1].strip()

    if not bot_token:
        print("\n[!] Токен Telegram-бота не задан.")
        bot_token = input("Введите токен Telegram-бота (от @BotFather): ").strip()

    if not openrouter_key:
        print("\n[!] Ключ OpenRouter API не задан.")
        openrouter_key = input("Введите API-ключ OpenRouter (ключ из личного кабинета): ").strip()


    # Save to .env
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"# LucidBot Environment Configuration\n")
        f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
        f.write(f"OPENROUTER_API_KEY={openrouter_key}\n")
        f.write(f"FORGE_API_URL=http://127.0.0.1:7860\n")
    print("[+] Файл .env успешно сохранён.")

    # 5. Launch Option
    print_header("Запуск LucidBot")
    launch = input("\n[?] Запустить бота прямо сейчас? [y/n] (по умолчанию: y): ").strip().lower()
    if launch in ("", "y", "yes", "д", "да"):
        print("[*] Запуск LucidBot...")
        main_py = os.path.join(os.path.dirname(__file__), "main.py")
        subprocess.run([venv_python, main_py])

if __name__ == "__main__":
    main()
