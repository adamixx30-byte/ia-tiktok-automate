import os
import sys
import requests
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# -----------------------------------------------------------
# 🧠 Étape 1 : Récupérer le sujet (depuis le titre de l'issue)
# -----------------------------------------------------------
if len(sys.argv) < 2:
    print("⚠️ Aucun sujet fourni.")
    sys.exit(1)

subject = sys.argv[1]
print(f"🎯 Sujet reçu : {subject}")

# -----------------------------------------------------------
# 🧠 Étape 2 : Générer un texte via l’IA Hugging Face
# -----------------------------------------------------------
print("✍️ Génération du script avec l'IA...")

API_URL = "https://api-inference.huggingface.co/models/gpt2"
headers = {"Authorization": f"Bearer {os.environ.get('HF_TOKEN')}"}

prompt = f"Écris un court script informatif et captivant (50 secondes max) pour une vidéo TikTok sur : {subject}."

response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
script = response.json()[0]["generated_text"]

# Nettoyage du texte
script = script.strip().split("\n")[0]
print("🗒️ Script généré :")
print(script)

# -----------------------------------------------------------
# 🖼️ Étape 3 : Générer une image illustrant le sujet
# -----------------------------------------------------------
print("🧠 Génération d'une image avec Hugging Face...")

IMG_API = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
img_payload = {"inputs": subject}
img_response = requests.post(IMG_API, headers=headers, json=img_payload)

# Sauvegarde de l'image
with open("image.jpg", "wb") as f:
    f.write(img_response.content)

print("✅ Image générée et enregistrée sous image.jpg")

# -----------------------------------------------------------
# 🔊 Étape 4 : Générer la voix avec gTTS (Google Text-to-Speech)
# -----------------------------------------------------------
print("🎤 Génération de la voix...")

tts = gTTS(script, lang="fr")
tts.save("audio.mp3")
print("✅ Voix enregistrée sous audio.mp3")

# -----------------------------------------------------------
# 🎬 Étape 5 : Assembler la vidéo avec MoviePy
# -----------------------------------------------------------
print("🎬 Assemblage de la vidéo...")

# Charger les médias
clip = ImageClip("image.jpg", duration=50)
audio = AudioFileClip("audio.mp3")

# Adapter la durée à celle de l'audio
clip = clip.set_duration(audio.duration)
clip = clip.set_audio(audio)

# Exporter la vidéo
clip.write_videofile("final_video.mp4", fps=24)
print("✅ Vidéo finale générée : final_video.mp4")
