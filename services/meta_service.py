import requests
import dotenv
import os

dotenv.load_dotenv()

class WhatsAppAdapter:
    def __init__(self, token: str, phone_number_id: str):
        self.base_url = f"https://graph.facebook.com/v21.0/{phone_number_id}"
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def send_text(self, recipient_id: str, message: str):
        print(f"--------------Enviando mensaje a {recipient_id}: {message}--------------")
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message}
        }
        r = requests.post(url, headers=self.headers, json=payload)
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text)
        return r.json()

    def send_template(self, to: str, template: str, lang="es_AR"):
        url = f"{self.base_url}/messages?access_token={self.token}"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": lang}
            }
        }
        r = requests.post(url, headers=self.headers, json=payload)
        return r.json()


class WhatsAppChatAdapter:
    def __init__(self, client: WhatsAppAdapter):
        self.client = client

    def normalize_number(self, wa_id: str) -> str:
        """
        Convierte un wa_id tipo 5493585162235 a 543585162235 (solo para Argentina)
        """
        if wa_id.startswith("549") and len(wa_id) == 13:
            return "54" + wa_id[3:]
        return wa_id

    def send_message(self, user_id: str, text: str):
        normalized_id = self.normalize_number(user_id)
        return self.client.send_text(normalized_id, text)

    def receive_message(self, data: dict):
        try:
            entry = data["entry"][0]["changes"][0]["value"]
            if "messages" in entry:
                msg = entry["messages"][0]
                return {
                    "from": msg["from"],
                    "text": msg.get("text", {}).get("body", "")
                }
        except Exception as e:
            print("Error procesando mensaje:", e)
        return None


wa_client = WhatsAppAdapter(token=os.getenv("ACCES_TOKEN"), phone_number_id=os.getenv("PHONE_NUMBER_ID"))
whatsapp_adapter = WhatsAppChatAdapter(wa_client)
