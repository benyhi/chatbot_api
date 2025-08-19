from flask import Flask, request, jsonify, Response
from services.bot_service import ChatBot
import os

app = Flask(__name__)

# Inicializacion del bot
bot = ChatBot(api_key=os.getenv("API_KEY"))

# Devuelve la respuesta del chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    thread_id = data.get("thread_id", "001")

    if not user_message:
        return jsonify({"error": "Falta el parámetro 'message'"}), 400

    response = bot.chat(user_message, thread_id=thread_id)
    return jsonify({"response": response})

# Devuelve el historial de mensajes de un hilo
@app.route("/history/<thread_id>", methods=["GET"])
def history(thread_id):
    history = bot.get_history(thread_id)
    return jsonify({"thread_id": thread_id, "history": history})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
