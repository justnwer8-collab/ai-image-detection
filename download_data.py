import io
import os
import time
import urllib.parse
import urllib.request
from PIL import Image

REAL_DIR = "dataset/real"
AI_DIR = "dataset/ai_generated"
TARGET_AI_COUNT = 40
TARGET_REAL_COUNT = 20

AI_PROMPTS = [
    "realistic photograph of a modern city street at dusk",
    "close up portrait with studio lighting realistic photo",
    "futuristic architecture glass building daylight photo",
    "cozy wooden cabin in snowy mountains realistic photo",
    "artisan coffee cup on wooden table natural light",
    "vintage car parked near coastal road realistic photo",
    "minimalist scandinavian living room interior photo",
    "vibrant night market food stalls realistic photograph",
]


def save_image_from_url(url, out_path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.save(out_path, format="JPEG")


def count_existing_jpgs(folder):
    if not os.path.exists(folder):
        return 0
    return len([f for f in os.listdir(folder) if f.lower().endswith(".jpg")])


def main():
    os.makedirs(REAL_DIR, exist_ok=True)
    os.makedirs(AI_DIR, exist_ok=True)

    real_saved = count_existing_jpgs(REAL_DIR)
    ai_saved = count_existing_jpgs(AI_DIR)

    # تحميل صور حقيقية إضافية إذا كانت أقل من المطلوب
    idx = 1
    while real_saved < TARGET_REAL_COUNT and idx <= 100:
        real_path = os.path.join(REAL_DIR, f"real_{idx}.jpg")
        if not os.path.exists(real_path):
            real_url = f"https://picsum.photos/256/256?random={500 + idx}"
            try:
                save_image_from_url(real_url, real_path)
                real_saved += 1
            except Exception:
                pass
        idx += 1

    # تحميل صور ذكاء اصطناعي حتى الوصول للعدد المطلوب
    ai_idx = 1
    attempts = 0
    max_attempts = TARGET_AI_COUNT * 4

    while ai_saved < TARGET_AI_COUNT and attempts < max_attempts:
        attempts += 1
        ai_path = os.path.join(AI_DIR, f"ai_{ai_idx}.jpg")
        ai_idx += 1

        if os.path.exists(ai_path):
            continue

        prompt_base = AI_PROMPTS[(attempts - 1) % len(AI_PROMPTS)]
        encoded_prompt = urllib.parse.quote(f"{prompt_base} variation {attempts}")
        ai_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=256&height=256&nologo=true&seed={1000 + attempts}"
        )

        try:
            save_image_from_url(ai_url, ai_path)
            ai_saved += 1
            print(f"تم حفظ صورة AI رقم {ai_saved} من {TARGET_AI_COUNT}")
            time.sleep(0.3)
        except Exception:
            time.sleep(0.5)

    print(f"العدد النهائي الآن -> real: {real_saved} | ai_generated: {ai_saved}")


if __name__ == "__main__":
    main()