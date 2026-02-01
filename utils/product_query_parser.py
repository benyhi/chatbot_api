# services/product_query_parser.py
"""
Product Query Parser
--------------------
Convierte una consulta en lenguaje natural a una estructura JSON con filtros
útiles para la búsqueda híbrida (filtrado + semantic search).

Requiere:
- Tener la variable de entorno API_KEY configurada.
- Tener instalada la dependencia que ya usaste: langchain_openai (ChatOpenAI).

Salida (ejemplo):
{
  "categoria": "Remeras",
  "color": "Rojo",
  "talle": "M",
  "precio": {"gte": 10000, "lte": 20000},   # opcional
  "stock_min": 1,                           # opcional
  "marca": "Nike",
  "genero": "Mujer",
  "material": "Algodón",
  "consulta_texto": "remera roja talle M",
  "limit": 8
}
"""

import os
import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
import dotenv

dotenv.load_dotenv()

# Modelo corregido: gpt-4o-mini
LLM_MODEL = os.getenv("PARSER_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")

# Instanciamos el LLM
llm = ChatOpenAI(model=LLM_MODEL, temperature=0.0, api_key=OPENAI_API_KEY, streaming=False)


# Prompt que se le envía al LLM para que devuelva JSON estricto
PROMPT_TEMPLATE = """
Eres un parser. Recibís una consulta del usuario y devolvés SOLO un JSON válido,
sin explicaciones ni texto adicional. El JSON debe tener estas claves (si corresponde):
- categoria (string o null)
- color (string o null)
- talle (string o null)  # normalizá a XS,S,M,L,XL,XXL,XXXL si se puede
- precio (objeto con gte y/o lte, o null)  # ejemplo: {{ "gte": 10000, "lte": 20000 }}
- stock_min (int o null)
- marca (string o null)
- genero (string o null) # Hombre, Mujer, Unisex
- material (string o null)
- consulta_texto (string) # versión corta útil para embedding/semantic search
- limit (int) # cantidad de resultados deseada (default 8)

Reglas:
1. Si un campo no aparece en la consulta, devolvé null para ese campo.
2. Normalizá precios: si el usuario dice "entre 10k y 20k" devolvé números (10000,20000).
3. Para talles, convertí palabras como "mediano" -> "M", "grande" -> "L".
4. consulta_texto debe ser una frase corta representativa (palabras clave).
5. Devuelve solo JSON. Nada más.

Ejemplos de entrada/JSON:
- "Busco remera roja talle M para mujer" =>
  {{"categoria":"Remeras","color":"Rojo","talle":"M","precio":null,"stock_min":null,"marca":null,"genero":"Mujer","material":null,"consulta_texto":"remera roja talle M","limit":8}}

Ahora procesá esta consulta:
{query}
"""

def _call_llm_and_parse(query: str) -> Optional[Dict[str, Any]]:
    """
    Llama al LLM con el prompt y parsea la salida JSON.
    Retorna dict o None si falla.
    """
    prompt = PROMPT_TEMPLATE.format(query=query)
    
    # Llamada al LLM - ChatOpenAI devuelve un objeto AIMessage
    resp = llm.invoke(prompt)
    
    # Extraer el contenido del mensaje
    text_out = resp.content
    
    print(f"DEBUG - LLM Response: {text_out}")  # Para debug
    
    # El modelo debe devolver JSON; limpiamos y parseamos
    try:
        # a veces hay código o backticks: extraemos la primera llave { ... }
        start = text_out.find("{")
        end = text_out.rfind("}")
        json_str = text_out[start:end+1] if start != -1 and end != -1 else text_out
        parsed = json.loads(json_str)
        return parsed
    except Exception as e:
        print(f"DEBUG - JSON Parse Error: {e}")  # Para debug
        return None


# Utilidad para normalizar talles básicos
_TALLE_MAP = {
    "xs": "XS", "extra chico": "XS", "extra small": "XS",
    "s": "S", "small": "S", "chico": "S",
    "m": "M", "mediano": "M", "medium": "M",
    "l": "L", "grande": "L", "large": "L",
    "xl": "XL", "extra large": "XL",
    "xxl": "XXL", "xxxl": "XXXL",
}

def normalize_talle(t: Optional[str]) -> Optional[str]:
    if not t:
        return None
    t_clean = t.strip().lower()
    return _TALLE_MAP.get(t_clean, t.strip().upper())


# Función pública principal
def parse_user_query(user_text: str, default_limit: int = 8) -> Dict[str, Any]:
    """
    Devuelve el dict de filtros a usar downstream.
    Si el parser falla, tratamos de devolver al menos una consulta_texto simple.
    """
    parsed = _call_llm_and_parse(user_text)

    # Si LLM falló en devolver JSON, hacemos heurística simple
    if not parsed:
        # Heurística fallback mínima:
        fallback = {
            "categoria": None,
            "color": None,
            "talle": None,
            "precio": None,
            "stock_min": None,
            "marca": None,
            "genero": None,
            "material": None,
            "consulta_texto": user_text,
            "limit": default_limit
        }
        return fallback

    # Normalizaciones y saneamiento
    # talles
    if parsed.get("talle"):
        parsed["talle"] = normalize_talle(parsed["talle"])
    else:
        parsed["talle"] = None

    # precio: asegurar formato {gte?:num, lte?:num} o None
    price = parsed.get("precio")
    if isinstance(price, dict):
        # intentar convertir a números
        clean = {}
        if price.get("gte") is not None:
            try:
                clean["gte"] = int(price["gte"])
            except:
                pass
        if price.get("lte") is not None:
            try:
                clean["lte"] = int(price["lte"])
            except:
                pass
        parsed["precio"] = clean if clean else None
    else:
        parsed["precio"] = None

    # limit
    try:
        parsed["limit"] = int(parsed.get("limit") or default_limit)
    except:
        parsed["limit"] = default_limit

    # garantizar keys presentes
    for k in ["categoria", "color", "stock_min", "marca", "genero", "material", "consulta_texto"]:
        if k not in parsed:
            parsed[k] = None

    return parsed


# ============================
# Ejemplo de uso (para pruebas)
# ============================
if __name__ == "__main__":
    examples = [
        "Tenés una remera roja talle M para mujer?",
        "Busco zapatillas nike entre 20000 y 40000, talle 42",
        "Campera azul para hombre, preferentemente de lana",
        "Remera oversize negra, marca adidas, precio hasta 15000"
    ]

    for q in examples:
        out = parse_user_query(q)
        print("QUERY:", q)
        print("PARSED:", json.dumps(out, indent=2, ensure_ascii=False))
        print("-" * 40)
