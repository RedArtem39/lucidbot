import os
import aiohttp
import re
import json
from typing import List, Dict, Optional, Tuple

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Primary: DeepSeek V4 Flash 0731 | Backup: Latest Gemini Flash Lite
PRIMARY_MODEL = "deepseek/deepseek-v4-flash-0731"
BACKUP_MODEL = "google/gemini-3.5-flash-lite"

class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")

    def set_api_key(self, key: str):
        self.api_key = key.strip()

    async def generate_reply(
        self,
        system_prompt: str,
        history: List[Dict[str, str]],
        user_message: str,
        temperature: float = 0.85,
        is_tier3: bool = False
    ) -> Tuple[str, List[str]]:
        if not self.api_key:
            return "[Ошибка: API-ключ OpenRouter не настроен. Укажите OPENROUTER_API_KEY в .env]", []

        tier3_instruction = ""
        if is_tier3:
            tier3_instruction = (
                "\n\n[MANDATORY FORMATTING RULE FOR TIER 3]:\n"
                "Write your descriptive, sensual roleplay response in Russian.\n"
                "Then, at the very end of your message, you MUST include exactly 3 short spicy action choices for the user, separated by [CHOICES]. Example:\n"
                "*descriptive text*\n"
                "[CHOICES]\n"
                "1. First spicy action\n"
                "2. Second spicy action\n"
                "3. Third spicy action"
            )

        messages = [{"role": "system", "content": system_prompt + tier3_instruction}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://lucidbot.telegram",
            "X-Title": "LucidBot AI Companion",
            "Content-Type": "application/json"
        }

        # Try Primary Model (DeepSeek V4 Flash) -> Then Backup (Gemini 3.5 Flash Lite)
        models_to_try = [PRIMARY_MODEL, BACKUP_MODEL]
        last_error = ""

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 700,
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            choices_list = data.get("choices", [])
                            if choices_list and "message" in choices_list[0]:
                                content = choices_list[0]["message"].get("content", "").strip()
                                if content:
                                    main_text, suggestions = self._parse_choices(content, is_tier3)
                                    return main_text, suggestions
                        else:
                            last_error = f"OpenRouter {model} returned status {resp.status}"
            except Exception as e:
                last_error = str(e)
                continue

        return f"[Не удалось получить ответ: {last_error}]", []

    def _parse_choices(self, raw_text: str, is_tier3: bool) -> Tuple[str, List[str]]:
        if not is_tier3:
            return raw_text, []

        suggestions = []
        main_text = raw_text

        if "[CHOICES]" in raw_text:
            parts = raw_text.split("[CHOICES]")
            main_text = parts[0].strip()
            choices_block = parts[1].strip()
            lines = [l.strip() for l in choices_block.split("\n") if l.strip()]
            for l in lines:
                cleaned = re.sub(r"^\d+[\.\)]\s*", "", l).strip()
                cleaned = re.sub(r"^[-*•]\s*", "", cleaned).strip()
                if cleaned:
                    suggestions.append(cleaned)
        else:
            lines = raw_text.split("\n")
            extracted = []
            cut_idx = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()
                if re.match(r"^\d+[\.\)]\s+", line):
                    extracted.insert(0, re.sub(r"^\d+[\.\)]\s*", "", line))
                    cut_idx = i
                elif extracted:
                    break

            if len(extracted) >= 2:
                suggestions = extracted[:3]
                main_text = "\n".join(lines[:cut_idx]).strip()

        # Fallback default spicy suggestions if model didn't provide any
        if is_tier3 and len(suggestions) < 2:
            suggestions = [
                "Приказать ей полностью раздеться и подойти ближе",
                "Страстно поцеловать её и повалить на кровать",
                "Взять её за подбородок и прошептать своё сокровенное желание"
            ]

        return main_text, suggestions[:3]

    async def generate_photo_prompt(self, character_tags: str, last_context: str) -> str:
        """Translates current roleplay scene into Danbooru tags for Forge rendering."""
        if not self.api_key:
            return f"{character_tags}, looking at viewer, masterpiece, best quality"

        sys_p = (
            "You are an expert anime Danbooru tag generator for SDXL Pony / AutismMix. "
            "Your job is to translate the current roleplay scene into precise Danbooru tags representing the character's exact visual state:\n"
            "GENDER & ANATOMY RULES:\n"
            "- If the character is MALE (1man, old man, boy): for nudity/sex/gachi use `1man, nude, completely nude, penis, testicles, hairy chest, bare skin` (NEVER use pussy or breasts for male!).\n"
            "- If the character is FEMALE (1girl): for nudity use `1girl, nude, completely nude, nipples, bare breasts, pussy, bare skin`.\n"
            "ACTION RULES:\n"
            "- If oral sex / blowjob / минет / отсоси / lick / sucking is mentioned: output `blowjob, fellatio, kneeling, looking up, open mouth, saliva, drooling, blush, sweat, seductive gaze, close-up, nude`.\n"
            "- If sex / gachi / intercourse / doggystyle / missionary is mentioned: output `sex, missionary, from behind, spreading legs, heavy sweat, nude`.\n"
            "- If partially undressed: output `unbuttoned shirt, taking off shirt, underwear, bare shoulders`.\n"
            "- If fully clothed: describe the exact outfit from the scene.\n"
            "Always include pose, expression, and environment tags (e.g. `sweat, looking at viewer, dim dungeon cell, masterpiece, best quality`).\n"
            "Output ONLY the comma-separated Danbooru tags."
        )


        user_p = f"Character features: {character_tags}\nRecent Scene Context:\n{last_context}\nDanbooru Tags:"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek/deepseek-chat",
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": user_p}
            ],
            "temperature": 0.4,
            "max_tokens": 140
        }

        for model in ["deepseek/deepseek-chat", "mistralai/mistral-nemo", "google/gemini-3.5-flash-lite"]:
            payload["model"] = model
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            tags = data["choices"][0]["message"]["content"].strip()
                            return f"{character_tags}, {tags}"
            except Exception:
                continue

        return f"{character_tags}, seductive expression, bedroom, masterpiece, best quality"

