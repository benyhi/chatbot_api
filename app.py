from flask import Flask, request, jsonify
from flask_cors import CORS
from database import SessionLocal, engine
from database.models import Message, Base  # Importa Base
from database.db_saver import get_memory_saver
from services.bot_service import ChatBot
from services.meta_service import whatsapp_adapter
import dotenv
import os

dotenv.load_dotenv()

app = Flask(__name__)
CORS(app)

Base.metadata.create_all(bind=engine)

memory = get_memory_saver()
memory.setup()

bot = ChatBot()

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == os.getenv("VERIFY_TOKEN"):
        return challenge, 200
    else:
        return "Error: token inválido", 403

# Recepción de mensajes entrantes
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Mensaje entrante:", data)

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            if messages and contacts:

                response = bot.chat(messages[0].get("text", {}).get("body", ""), "001")
                print("Respuesta del bot:", response)
                if response:
                    whatsapp_adapter.send_message(
                        user_id=contacts[0]["wa_id"],
                        text=response
                    )
                else:
                    text = messages[0].get("text", {}).get("body", "")
                    print(f"Mensaje de {contacts[0]['wa_id']}: {text}")

                    whatsapp_adapter.send_message(
                        user_id=contacts[0]["wa_id"],
                        text="¡Hola! Gracias por tu mensaje 🚀"
                    )

    return jsonify({"status": "ok"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    thread_id = data.get("thread_id", "001")

    if not user_message:
        return jsonify({"error": "Falta el parámetro 'message'"}), 400

    response = bot.chat(user_message, thread_id)
    return jsonify({"response": response})


@app.route("/history/<thread_id>", methods=["GET"])
def history(thread_id):
    db = SessionLocal()
    messages = (
        db.query(Message)
        .filter_by(thread_id=thread_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    db.close()
    return jsonify({
        "thread_id": thread_id,
        "history": [{"role": m.role, "content": m.content} for m in messages]
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
