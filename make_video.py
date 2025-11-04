import os
import sys
import requests
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip

# -----------------------------------------------------------
# 🧠 Étape 1 : Récupérer le sujet depuis l'entrée
# -----------------------------------------------------------
if len(sys.argv) < 2:
    print("⚠️ Aucun sujet fourni.")
    sys.exit(1)

subject = sys.argv[1]
print(f"🎯 Sujet : {subject}")

# -----------------------------------------------------------
# 🧠 Étape 2 : Générer un script avec un modèle IA (Hugging Face)
# -----------------------------------------------------------
print("✍️ Appel à l'API texte Hugging Face...")

API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
headers = {
    "Authorization": f"Bearer {os.environ.get('HF_TOKEN')}",
    "Content-Type": "application/json"
}

prompt = f"Écris un court script informatif et captivant (environ 50 secondes de lecture) pour une vidéo TikTok sur : {subject}."

payload = {
    "inputs": prompt,
    "parameters": {
        "max_new_tokens": 250,
        "temperature": 0.7,
        "do_sample": True
    }
}

response = requests.post(API_URL, headers=headers, json=payload)

if response.status_code != 200:
    print(f"❌ Erreur Hugging Face ({response.status_code}): {response.text}")
    sys.exit(1)

try:
    data = response.json()
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

# -----------------------------------------------------------
# 🖼️ Étape 3 : Générer une image avec Hugging Face
# -----------------------------------------------------------
print("🎨 Génération d'une image...")

IMG_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
img_payload = {"inputs": subject}
img_response = requests.post(IMG_URL, headers=headers, json=img_payload)

if img_response.status_code != 200:
    print(f"❌ Erreur génération image ({img_response.status_code}): {img_response.text}")
    sys.exit(1)

with open("image.jpg", "wb") as f:
    f.write(img_response.content)
print("✅ Image générée : image.jpg")

# -----------------------------------------------------------
# 🔊 Étape 4 : Générer la voix (gTTS)
# -----------------------------------------------------------
print("🎤 Génération de la voix...")
tts = gTTS(script, lang="fr")
tts.save("audio.mp3")
print("✅ Voix enregistrée : audio.mp3")

# -----------------------------------------------------------
# 🎬 Étape 5 : Assembler la vidéo (MoviePy)
# -----------------------------------------------------------
print("🎬 Assemblage de la vidéo...")
clip = ImageClip("image.jpg", duration=50)
audio = AudioFileClip("audio.mp3")
clip = clip.set_duration(audio.duration)
clip = clip.set_audio(audio)
clip.write_videofile("final_video.mp4", fps=24)
print("✅ Vidéo finale générée : final_video.mp4")
