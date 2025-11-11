import requests
import json

BASE_URL = "http://127.0.0.1:5000"  # tu Flask local
THREAD_ID = "001"

test_messages = [
    "Hola, como estas?",
    "Queria hacerte una consulta",
    "Tenés remera roja talle M?",
    "Qué stock hay de pantalón jean azul?",
    "Busco zapatillas talla 42 color blanco",
    "Cuánto cuesta un sweater de lana?",
    "Hola, contame un chiste"
]

for msg in test_messages:
    payload = {
        "message": msg,
        "thread_id": THREAD_ID
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nUsuario: {msg}")
        print(f"Bot: {data.get('response')}")
    else:
        print(f"Error {response.status_code}: {response.text}")
    
    # Espera antes de enviar el siguiente mensaje
    input("\nPresiona Enter para enviar el siguiente mensaje...")
