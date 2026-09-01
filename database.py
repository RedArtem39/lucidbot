import time
import aiosqlite
from typing import Optional, Dict, List, Tuple

DB_PATH = "lucid.db"



SECRET_PROMO = "123bab212"
PROMO_DURATION_DAYS = 7

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            energy INTEGER DEFAULT 25,
            photo_energy INTEGER DEFAULT 5,
            last_refill INTEGER,
            is_unlimited INTEGER DEFAULT 0,
            unlimited_until INTEGER DEFAULT 0,
            active_character_id TEXT DEFAULT 'elena',
            created_at INTEGER
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            character_id TEXT,
            role TEXT,
            content TEXT,
            timestamp INTEGER
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT,
            tagline TEXT,
            category TEXT,
            avatar_url TEXT,
            prompt_tags TEXT,
            system_prompt TEXT,
            greeting TEXT,
            affection_base INTEGER DEFAULT 0
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_characters (
            user_id INTEGER,
            character_id TEXT,
            affection INTEGER DEFAULT 10,
            PRIMARY KEY (user_id, character_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_unlocked_characters (
            user_id INTEGER,
            character_id TEXT,
            unlocked_at INTEGER,
            PRIMARY KEY (user_id, character_id)
        )
        """)

        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS promo_activations (
            user_id INTEGER,
            promo_code TEXT,
            activated_at INTEGER,
            PRIMARY KEY (user_id, promo_code)
        )
        """)
        
        await db.commit()

async def get_or_create_user(user_id: int, username: str = "") -> Dict:
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                user = dict(row)
                # Check refill (24h refill)
                if now - user["last_refill"] > 86400 and not user["is_unlimited"]:
                    await db.execute(
                        "UPDATE users SET energy = 25, photo_energy = 5, last_refill = ? WHERE user_id = ?",
                        (now, user_id)
                    )
                    await db.commit()
                    user["energy"] = 25
                    user["photo_energy"] = 5
                    user["last_refill"] = now
                
                # Check unlimited expiration
                if user["is_unlimited"] and now > user["unlimited_until"]:
                    await db.execute(
                        "UPDATE users SET is_unlimited = 0, unlimited_until = 0 WHERE user_id = ?",
                        (user_id,)
                    )
                    await db.commit()
                    user["is_unlimited"] = 0
                    user["unlimited_until"] = 0
                    
                return user

        # New user
        await db.execute(
            "INSERT INTO users (user_id, username, energy, photo_energy, last_refill, is_unlimited, unlimited_until, active_character_id, created_at) "
            "VALUES (?, ?, 25, 5, ?, 0, 0, 'elena', ?)",
            (user_id, username or "", now, now)
        )
        await db.commit()
        return {
            "user_id": user_id,
            "username": username,
            "energy": 25,
            "photo_energy": 5,
            "last_refill": now,
            "is_unlimited": 0,
            "unlimited_until": 0,
            "active_character_id": "elena",
            "created_at": now
        }

async def set_active_character(user_id: int, character_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET active_character_id = ? WHERE user_id = ?", (character_id, user_id))
        await db.commit()

async def deduct_energy(user_id: int, is_photo: bool = False) -> bool:
    user = await get_or_create_user(user_id)
    if user["is_unlimited"]:
        return True

    key = "photo_energy" if is_photo else "energy"
    if user[key] <= 0:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {key} = {key} - 1 WHERE user_id = ?", (user_id,))
        await db.commit()
    return True

async def is_character_unlocked(user_id: int, character_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM user_unlocked_characters WHERE user_id = ? AND character_id = ?", (user_id, character_id)) as cursor:
            return bool(await cursor.fetchone())

async def get_unlocked_characters(user_id: int) -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT character_id FROM user_unlocked_characters WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def activate_promo(user_id: int, code: str) -> Tuple[bool, str]:
    clean_code = code.strip()
    now = int(time.time())
    user = await get_or_create_user(user_id)

    # 1. Promo: 3 / /3 (Unlocks Stepsister Alisa + 1 Day Unlimited)
    if clean_code.lower() in ["3", "/3"]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM promo_activations WHERE user_id = ? AND promo_code = '3'", (user_id,)) as cursor:
                if await cursor.fetchone():
                    return False, "Вы уже активировали промокод '/3'!"

            current_until = user["unlimited_until"] if user["is_unlimited"] else now
            new_until = max(now, current_until) + 86400  # 1 day unlimited
            
            await db.execute("UPDATE users SET is_unlimited = 1, unlimited_until = ?, active_character_id = 'stepsister_alisa' WHERE user_id = ?", (new_until, user_id))
            await db.execute("INSERT OR IGNORE INTO user_unlocked_characters (user_id, character_id, unlocked_at) VALUES (?, 'stepsister_alisa', ?)", (user_id, now))
            await db.execute("INSERT INTO promo_activations (user_id, promo_code, activated_at) VALUES (?, '3', ?)", (user_id, now))
            await db.commit()

        return True, (
            "🎀 <b>ПРОМОКОД АКТИВИРОВАН!</b>\n\n"
            "⚡ <b>Вы получили БЕЗЛИМИТ НА 1 ДЕНЬ (24 ЧАСА)!</b>\n"
            "🎭 <b>РАЗБЛОКИРОВАН СЕКРЕТНЫЙ ПЕРСОНАЖ:</b>\n"
            "<b>Алиса (Сводная сестра) 🎀 [18+ Хентай]</b>\n\n"
            "Она уже ждёт вас дома без белья и готова исполнять любые ваши желания!"
        )


    # 2. Promo: fem / /fem (Unlocks Catboy & Catgirl + 1 Day Unlimited)
    elif clean_code.lower() in ["fem", "/fem", "femme"]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM promo_activations WHERE user_id = ? AND promo_code = 'fem'", (user_id,)) as cursor:
                if await cursor.fetchone():
                    return False, "Вы уже активировали промокод '/fem'!"

            current_until = user["unlimited_until"] if user["is_unlimited"] else now
            new_until = max(now, current_until) + 86400  # 1 day unlimited
            
            await db.execute("UPDATE users SET is_unlimited = 1, unlimited_until = ?, active_character_id = 'catboy_felix' WHERE user_id = ?", (new_until, user_id))
            await db.execute("INSERT OR IGNORE INTO user_unlocked_characters (user_id, character_id, unlocked_at) VALUES (?, 'catboy_felix', ?)", (user_id, now))
            await db.execute("INSERT OR IGNORE INTO user_unlocked_characters (user_id, character_id, unlocked_at) VALUES (?, 'catgirl_nyan', ?)", (user_id, now))
            await db.execute("INSERT INTO promo_activations (user_id, promo_code, activated_at) VALUES (?, 'fem', ?)", (user_id, now))
            await db.commit()

        return True, (
            "🐾 <b>ПРОМОКОД АКТИВИРОВАН!</b>\n\n"
            "⚡ <b>Вы получили БЕЗЛИМИТ НА 1 ДЕНЬ (24 ЧАСА)!</b>\n"
            "🎭 <b>РАЗБЛОКИРОВАНЫ СЕКРЕТНЫЕ ПЕРСОНАЖИ:</b>\n"
            "1. <b>Феликс (Catboy) 🐾♂️</b> — покорный кошко-мальчик (активен сейчас!)\n"
            "2. <b>Няночка (Catgirl) 🐾♀️</b> — страстная неко-тян\n\n"
            "Они уже доступны в каталоге и готовы исполнять любые ваши желания!"
        )


    # 2. Secret Promo: 123bab212 (7 Days Unlimited)
    elif clean_code == SECRET_PROMO:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM promo_activations WHERE user_id = ? AND promo_code = ?", (user_id, clean_code)) as cursor:
                if await cursor.fetchone():
                    return False, "Вы уже активировали этот промокод!"

            until = now + (PROMO_DURATION_DAYS * 86400)
            await db.execute("UPDATE users SET is_unlimited = 1, unlimited_until = ? WHERE user_id = ?", (until, user_id))
            await db.execute("INSERT INTO promo_activations (user_id, promo_code, activated_at) VALUES (?, ?, ?)", (user_id, clean_code, now))
            await db.commit()

        return True, f"Промокод активирован! Вы получили безлимитный доступ на {PROMO_DURATION_DAYS} дней."

    return False, "Неверный промокод!"




async def save_message(user_id: int, character_id: str, role: str, content: str):
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, character_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (user_id, character_id, role, content, now)
        )
        await db.commit()

async def get_history(user_id: int, character_id: str, limit: int = 12) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content FROM messages WHERE user_id = ? AND character_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, character_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

async def clear_history(user_id: int, character_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE user_id = ? AND character_id = ?", (user_id, character_id))
        await db.commit()

async def get_affection(user_id: int, character_id: str, default_base: int = 10) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT affection FROM user_characters WHERE user_id = ? AND character_id = ?", (user_id, character_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
        return default_base


async def add_affection(user_id: int, character_id: str, amount: int = 2) -> int:
    current = await get_affection(user_id, character_id)
    new_aff = min(100, current + amount)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_characters (user_id, character_id, affection) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, character_id) DO UPDATE SET affection = ?",
            (user_id, character_id, new_aff, new_aff)
        )
        await db.commit()
    return new_aff

class Tuple_Result(tuple):
    pass
