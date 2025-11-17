import os
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from openai import OpenAI
import uuid

app = Flask(__name__)
CORS(app)

# ===========================================
# 🔥 CONFIG OPENAI — CHAVE DIRETO NO CÓDIGO
# ===========================================
OPENAI_KEY = "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"  # <<< COLOQUE AQUI A SUA KEY

client = OpenAI(api_key=OPENAI_KEY)


@app.route("/")
def home():
    return "API Assistente Rural IA rodando corretamente!"


@app.route("/processar-audio", methods=["POST"])
def processar_audio():
    if "audio" not in request.files:
        return jsonify({"error": "Nenhum áudio enviado"}), 400

    audio_file = request.files["audio"]
    temp_path = f"temp_{uuid.uuid4()}.webm"
    audio_file.save(temp_path)

    try:
        # ------------------------------------
        # 1️⃣ TRANSCRIÇÃO (Whisper novo)
        # ------------------------------------
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=open(temp_path, "rb")
        )

        texto_usuario = transcription.text
        print("Usuário disse:", texto_usuario)

        # ------------------------------------
        # 2️⃣ RESPOSTA GPT
        # ------------------------------------
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um especialista em agricultura. Responda de forma clara e direta."
                },
                {
                    "role": "user",
                    "content": texto_usuario
                }
            ]
        )

        texto_resposta = resposta.choices[0].message["content"]
        print("Resposta:", texto_resposta)

        # ------------------------------------
        # 3️⃣ TTS — Texto para Áudio
        # ------------------------------------
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=texto_resposta,
            format="mp3"
        )

        output_path = f"resposta_{uuid.uuid4()}.mp3"
        with open(output_path, "wb") as f:
            f.write(speech.read())

        # ------------------------------------
        # 4️⃣ Enviar para o frontend
        # ------------------------------------
        return send_file(output_path, mimetype="audio/mp3")

    except Exception as e:
        print("ERRO:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            os.remove(temp_path)
        except:
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
