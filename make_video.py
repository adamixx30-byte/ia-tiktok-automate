# make_video.py - version robuste pour GitHub Actions
import os
import sys
import requests
import subprocess
import time
from gtts import gTTS

OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

def safe_exit(msg, code=1):
    print("❌", msg)
    sys.exit(code)

# 1) Récupérer le sujet (arg)
if len(sys.argv) < 2:
    safe_exit("Aucun sujet fourni en argument. Usage: python make_video.py \"Mon sujet\"")

subject = sys.argv[1]
print("🎯 Sujet :", subject)

# -----------------------------------------------------------
# 🧠 Étape 2 : Générer un texte via l’IA Hugging Face (Text Generation)
# -----------------------------------------------------------
print("✍️ Appel à l'API texte Hugging Face...")

API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
headers = {
    "Authorization": f"Bearer {os.environ.get('HF_TOKEN')}",
    "Content-Type": "application/json"
}

prompt = f"Écris un court script informatif et captivant (50 secondes max) pour une vidéo TikTok sur : {subject}."

payload = {
    "inputs": prompt,
    "parameters": {"max_new_tokens": 200, "temperature": 0.7, "do_sample": True}
}

response = requests.post(API_URL, headers=headers, json=payload)

if response.status_code != 200:
    print(f"❌ Erreur Hugging Face ({response.status_code}): {response.text}")
    sys.exit(1)

try:
    data = response.json()
    # Plusieurs formats possibles selon le modèle
    if isinstance(data, list) and "generated_text" in data[0]:
        script = data[0]["generated_text"]
    elif isinstance(data, dict) and "generated_text" in data:
        script = data["generated_text"]
    else:
        script = data if isinstance(data, str) else str(data)
except Exception as e:
    print("❌ Erreur de parsing JSON :", e)
    print("Réponse brute :", response.text)
    sys.exit(1)

script = script.strip()
print("🗒️ Script généré :")
print(script)



# 3) Générer le script texte via Hugging Face (GPT-2 ou un modèle texte)
API_URL = "https://router.huggingface.co/hf-inference/models/google/gemma-2b-it"

prompt = f"Écris un court script informatif et captivant (≈45-55s) pour une vidéo TikTok sur : {subject}"

print("✍️ Appel à l'API texte Hugging Face...")
try:
    r = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=60)
except Exception as e:
    safe_exit(f"Erreur réseau lors de l'appel texte HF: {e}")

print("→ status", r.status_code)
try:
    data = r.json()
except Exception:
    safe_exit(f"Réponse texte non JSON (status {r.status_code}): {r.text[:400]}")

# Cas d'erreur renvoyée par HF
if isinstance(data, dict) and data.get("error"):
    safe_exit(f"HuggingFace error: {data.get('error')}")

# Récupération texte (divers formats possibles)
script = None
if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
    script = data[0]["generated_text"]
elif isinstance(data, dict) and "generated_text" in data:
    script = data["generated_text"]
else:
    # fallback : si la réponse est texte brut dans 'data'
    if isinstance(data, str):
        script = data
    else:
        safe_exit(f"Réponse inattendue de l'API texte: {data}")

script = script.strip()
# Raccourcir au premier paragraphe si trop long
script = script.split("\n")[0]
print("🗒 Script extrait (preview 400 chars):")
print(script[:400])

# 4) Générer une image via Hugging Face (Stable Diffusion)
IMG_API = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-2"
img_payload = {"inputs": subject}
print("🖼️ Appel API image :", IMG_API)
try:
    r_img = requests.post(IMG_API, headers=headers, json=img_payload, timeout=120)
except Exception as e:
    print("⚠️ Erreur réseau image:", e)
    r_img = None

image_path = os.path.join(OUT_DIR, "image.jpg")

if r_img is None:
    print("⚠️ Pas de réponse image, on prend fallback.")
    # fallback image random
    fallback = requests.get("https://picsum.photos/720/1280")
    with open(image_path, "wb") as f:
        f.write(fallback.content)
else:
    print("→ image status", r_img.status_code)
    # Si content-type indique une image, sauvegarder
    ctype = r_img.headers.get("content-type", "")
    if ctype.startswith("image/"):
        with open(image_path, "wb") as f:
            f.write(r_img.content)
        print("✅ Image sauvegardée:", image_path)
    else:
        # Parfois HF renvoie JSON d'erreur ou loading
        try:
            j = r_img.json()
            print("⚠️ Réponse image JSON received:", j)
        except Exception:
            print("⚠️ Réponse image non JSON, head content:", r_img.text[:300])
        print("➡️ Utilisation d'une image fallback (picsum).")
        fallback = requests.get("https://picsum.photos/720/1280")
        with open(image_path, "wb") as f:
            f.write(fallback.content)

# 5) Générer l'audio avec gTTS
audio_path = os.path.join(OUT_DIR, "audio.mp3")
try:
    print("🔊 Génération audio avec gTTS...")
    tts = gTTS(script, lang="fr")
    tts.save(audio_path)
    print("✅ Audio sauvegardé:", audio_path)
except Exception as e:
    safe_exit(f"Erreur gTTS: {e}")

# 6) Assembler image + audio en vidéo verticale 9:16 (utilise ffmpeg)
final_video = os.path.join(OUT_DIR, "final_video.mp4")

# get audio duration via ffprobe
def get_audio_duration(path):
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ], stderr=subprocess.STDOUT)
        return float(out.strip())
    except Exception as e:
        print("⚠️ Impossible de lire la durée audio via ffprobe:", e)
        return None

audio_dur = get_audio_duration(audio_path) or 10.0
print("⏱ Audio duration:", audio_dur)

# create a short video from image with same duration
# Use ffmpeg to loop the image for audio_dur seconds and create 1080x1920
try:
    # resize image to 1080x1920, pad if necessary
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-t", f"{audio_dur}",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_video
    ]
    print("🔧 Lancement ffmpeg...")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print("✅ Vidéo générée:", final_video)
except subprocess.CalledProcessError as e:
    safe_exit(f"ffmpeg failed: {e}. stdout/stderr not captured here.")

# 7) Fin
print("🎉 Pipeline terminé. Fichier final :", final_video)
