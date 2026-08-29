import aiohttp
import base64
import io
from PIL import Image
from typing import Optional, Tuple

FORGE_API_URL = "http://127.0.0.1:7860"

async def generate_character_image(
    prompt: str,
    negative_prompt: str = "worst quality, low quality, bad anatomy, bad hands, distortion, text, watermark",
    width: int = 832,
    height: int = 1216,
    steps: int = 25,
    cfg_scale: float = 7.0
) -> Tuple[Optional[bytes], str]:
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler_name": "Euler a",
        "batch_size": 1,
        "n_iter": 1
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{FORGE_API_URL}/sdapi/v1/txt2img", json=payload, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    images = data.get("images", [])
                    if images:
                        img_bytes = base64.b64decode(images[0])
                        return img_bytes, "OK"
                    return None, "Forge не вернул изображение."
                return None, f"Forge API ошибка (код {resp.status})"
    except aiohttp.ClientConnectorError:
        return None, "Stable Diffusion Forge не запущен на 127.0.0.1:7860"
    except Exception as e:
        return None, f"Ошибка генерации: {str(e)}"
