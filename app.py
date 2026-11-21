import os
import pickle
from flask import Flask, render_template, request
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
MODEL_CANDIDATES = [
    os.path.join("models", "detector.pkl"),
    "detector.pkl",
]
IMG_SIZE = (32, 32)
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".jpe"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def is_allowed_file(filename):
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS


def get_pixels_list(img):
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())


def extract_features(img_path):
    with Image.open(img_path) as img:
        img = img.convert("RGB").resize(IMG_SIZE)
        pixels = get_pixels_list(img)
        total = len(pixels)
        r_mean = sum(p[0] for p in pixels) / (total * 255.0)
        g_mean = sum(p[1] for p in pixels) / (total * 255.0)
        b_mean = sum(p[2] for p in pixels) / (total * 255.0)
        return [r_mean, g_mean, b_mean]


def distance_sq(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def load_model():
    for path in MODEL_CANDIDATES:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return pickle.load(f)
    return None


def analyze_single_image(img_path, label_title, model):
    feat = extract_features(img_path)
    c0 = model["class_0_real"]
    c1 = model["class_1_ai"]

    d0 = distance_sq(feat, c0)
    d1 = distance_sq(feat, c1)

    is_real = d0 <= d1
    verdict = "صورة حقيقية (Real)" if is_real else "صورة مولّدة بالذكاء الاصطناعي (AI Generated)"

    # حساب مؤشر تقارب نسبي بسيط بين المركزين (0% إلى 100%)
    total_d = d0 + d1
    if total_d > 0:
        confidence_pct = round((1.0 - (min(d0, d1) / total_d)) * 100, 1)
    else:
        confidence_pct = 50.0

    return {
        "slot": label_title,
        "filename": os.path.basename(img_path),
        "verdict": verdict,
        "is_real": is_real,
        "d_real": round(d0, 5),
        "d_ai": round(d1, 5),
        "score_pct": confidence_pct,
        "rgb": [round(x, 3) for x in feat],
    }


def build_comparison_summary(res1, res2):
    if not res1 or not res2:
        return None

    if res1["is_real"] == res2["is_real"]:
        common_type = "حقيقية" if res1["is_real"] else "مولّدة بالذكاء الاصطناعي"
        return (
            f"كلتا الصورتين صُنّفتا كصور {common_type}. "
            f"الصورة الأولى أقرب بقيمة {res1['score_pct']}%، والصورة الثانية بقيمة {res2['score_pct']}%."
        )

    real_img = res1 if res1["is_real"] else res2
    ai_img = res2 if res1["is_real"] else res1
    return (
        f"تباين في التصنيف: ({real_img['slot']} - {real_img['filename']}) تميل للتصنيف الحقيقي، "
        f"بينما ({ai_img['slot']} - {ai_img['filename']}) تميل للتصنيف المولّد بالذكاء الاصطناعي."
    )


def save_uploaded_file(file_storage, prefix):
    if not file_storage or not file_storage.filename:
        return None, None
    if not is_allowed_file(file_storage.filename):
        return None, "صيغة الملف غير مدعومة. يرجى اختيار صورة (JPG, PNG, WEBP)."

    clean_name = os.path.basename(file_storage.filename)
    stored_name = f"{prefix}_{clean_name}"
    save_path = os.path.join(UPLOAD_FOLDER, stored_name)
    file_storage.save(save_path)
    return save_path, None


@app.route("/", methods=["GET", "POST"])
def index():
    model = load_model()
    model_ready = isinstance(model, dict) and "class_0_real" in model and "class_1_ai" in model

    res1 = None
    res2 = None
    comparison = None
    error_msg = None

    if request.method == "POST":
        if not model_ready:
            error_msg = "النموذج غير جاهز. يرجى تشغيل training/train.py أولاً."
        else:
            f1 = request.files.get("image_1")
            f2 = request.files.get("image_2")

            path1, err1 = save_uploaded_file(f1, "img1")
            path2, err2 = save_uploaded_file(f2, "img2")

            if err1 or err2:
                error_msg = err1 or err2
            elif not path1 and not path2:
                error_msg = "يرجى اختيار صورة واحدة على الأقل (أو صورتين للمقارنة)."
            else:
                if path1:
                    res1 = analyze_single_image(path1, "الصورة الأولى", model)
                if path2:
                    res2 = analyze_single_image(path2, "الصورة الثانية", model)
                if res1 and res2:
                    comparison = build_comparison_summary(res1, res2)

    return render_template(
        "index.html",
        model_ready=model_ready,
        res1=res1,
        res2=res2,
        comparison=comparison,
        error_msg=error_msg,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
