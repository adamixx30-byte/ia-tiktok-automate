# make_video.py
import os, requests, subprocess, time
from PIL import Image
from io import BytesIO
import math

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise Exception("HF_TOKEN env var missing")

SUBJECT = os.getenv("SUBJECT", "").strip()
if not SUBJECT:
    SUBJECT = "Actualité locale"

OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

# Read prompts
with open("prompts.txt", "r", encoding="utf-8") as f:
    prompts = [p.strip() for p in f.readlines() if p.strip()]

# Build script text from SUBJECT (template)
SCRIPT_TEXT = (
    f"{SUBJECT}. "
    "Dans cette vidéo : ce qu'il s'est passé, pourquoi ça compte, et ce que cela implique. "
    "Fin octobre 2025, de vastes opérations policières ont été menées contre des réseaux de trafic dans plusieurs favelas, avec des bilans lourds. "
    "Des résidents dénoncent l'usage excessif de la force et les risques pour les civils. "
    "La grande question : est-ce que la stratégie militaire suffit, ou faut-il des politiques sociales durables ? "
    "Abonne-toi pour des explications courtes et factuelles sur l'actualité mondiale."
)

# Build SRT blocks (approx equal durations; total ~55s)
TOTAL_DUR = 55.0
n_blocks = 5
block_dur = TOTAL_DUR / n_blocks

srt_blocks = []
sentences = [
    f"{SUBJECT}.",
    "Dans cette vidéo : ce qu'il s'est passé, pourquoi ça compte, et ce que cela implique.",
    "Fin octobre 2025, de vastes opérations policières ont été menées contre des réseaux de trafic dans plusieurs favelas, avec des bilans lourds.",
    "Des résidents dénoncent l'usage excessif de la force et les risques pour les civils.",
    "La grande question : est-ce que la stratégie militaire suffit, ou faut-il des politiques sociales durables ? Abonne-toi pour en savoir plus."
]

def fmt_time(t):
    h = int(t//3600)
    m = int((t%3600)//60)
    s = int(t%60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

for i, sent in enumerate(sentences):
    start = i * block_dur
    end = start + block_dur
    srt_blocks.append((i+1, fmt_time(start), fmt_time(end), sent))

srt_path = os.path.join(OUT_DIR, "subtitles.srt")
with open(srt_path, "w", encoding="utf-8") as f:
    for idx, start, end, text in srt_blocks:
        f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

# --- Generate images using Hugging Face Inference API
MODEL = "stabilityai/stable-diffusion-2"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
IMG_PATHS = []
print("Generating images...")
for i, prompt in enumerate(prompts):
    print("Prompt:", prompt)
    payload = {"inputs": prompt}
    r = requests.post(f"https://api-inference.huggingface.co/models/{MODEL}", headers=HEADERS, json=payload, timeout=120)
    if r.status_code != 200:
        print("HF error:", r.status_code, r.text)
        raise SystemExit(1)
    img = Image.open(BytesIO(r.content)).convert("RGB")
    img = img.resize((1080, 1920))
    p = os.path.join(OUT_DIR, f"img_{i:02d}.jpg")
    img.save(p, quality=90)
    IMG_PATHS.append(p)
    time.sleep(1)

# --- TTS with edge-tts
audio_path = os.path.join(OUT_DIR, "voice.mp3")
print("Generating audio via edge-tts...")
subprocess.run(["edge-tts", "--voice", "fr-FR-HenriNeural", "--text", SCRIPT_TEXT, "--write-media", audio_path], check=True)

# --- get audio duration
def get_duration(path):
    res = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    return float(res.stdout.strip())

audio_dur = get_duration(audio_path)
per_image = audio_dur / len(IMG_PATHS)

# create concat list
list_file = os.path.join(OUT_DIR, "list.txt")
with open(list_file, "w", encoding="utf-8") as f:
    for img in IMG_PATHS:
        f.write(f"file '{img}'\n")
        f.write(f"duration {per_image}\n")
    f.write(f"file '{IMG_PATHS[-1]}'\n")

video_tmp = os.path.join(OUT_DIR, "video_tmp.mp4")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-vsync", "vfr", "-pix_fmt", "yuv420p", video_tmp], check=True)

final = os.path.join(OUT_DIR, "final_video.mp4")
# mux audio
subprocess.run(["ffmpeg", "-y", "-i", video_tmp, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", final], check=True)

# embed subtitles as separate file (optional) - leave SRT in output for manual upload
print("Done. Video:", final)
print("Subtitles:", srt_path)
