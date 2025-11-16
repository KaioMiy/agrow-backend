import os
import openai
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS liberado para qualquer origem (Firebase, etc.)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- CONFIGURAÇÃO OPENAI ---
# Leia SEMPRE da variável de ambiente
openai.api_key = os.environ.get("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Defina a variável de ambiente OPENAI_API_KEY")

client = openai.OpenAI(api_key=openai.api_key)
# --------------------

# Se você NÃO precisa servir index/script/folha pelo Flask,
# pode até remover essas rotas. Elas não atrapalham, mas também não são usadas
# quando o frontend está no Firebase.

# --- ROTAS PARA TESTE LOCAL (opcional) ---
@app.route('/')
def home():
    return "API Assistente Rural IA - OK"

# --- ROTA DA API (O CÉREBRO) ---
@app.route('/processar-audio', methods=['POST'])
def processar_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "Nenhum arquivo de áudio enviado"}), 400

    audio_file = request.files['audio']
    temp_audio_path = "temp_recording.webm"
    audio_file.save(temp_audio_path)

    try:
        # === 1. ÁUDIO -> TEXTO (Whisper) ===
        with open(temp_audio_path, "rb") as f:
            transcricao = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        texto_usuario = transcricao.text
        print(f"Texto do Usuário: {texto_usuario}")

        # === 2. TEXTO -> TEXTO (GPT) ===
        resposta_chat = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um especialista em agricultura e cultivo. Responda de forma concisa e direta."
                },
                {
                    "role": "user",
                    "content": texto_usuario
                }
            ]
        )
        texto_resposta = resposta_chat.choices[0].message.content
        print(f"Texto da Resposta: {texto_resposta}")

        # === 3. TEXTO -> ÁUDIO (TTS) ===
        resposta_audio_stream = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=texto_resposta
        )

        path_resposta_audio = "response_audio.mp3"
        # dependendo da versão do SDK, pode ser write_to_file ou stream_to_file
        try:
            resposta_audio_stream.stream_to_file(path_resposta_audio)
        except AttributeError:
            # fallback para versões novas
            with open(path_resposta_audio, "wb") as f:
                f.write(resposta_audio_stream.read())

        # === 4. ENVIAR ÁUDIO DE VOLTA ===
        return send_file(path_resposta_audio, mimetype="audio/mp3")

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        if os.path.exists("response_audio.mp3"):
            # Se quiser, pode apagar depois de enviar
            pass


if __name__ == '__main__':
    # Render define a porta na variável PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
