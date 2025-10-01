from services.meta_service import WhatsAppChatAdapter, WhatsAppAdapter
import dotenv
import os

dotenv.load_dotenv()

whatsapp_adapter = WhatsAppAdapter(os.getenv("ACCES_TOKEN"), os.getenv("PHONE_NUMBER_ID"))
whatsapp_chat_adapter = WhatsAppChatAdapter(whatsapp_adapter)

whatsapp_chat_adapter.send_message("5493585162235", "Hola Benja! 🚀")
