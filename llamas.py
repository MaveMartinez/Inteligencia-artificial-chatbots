# llm.py
# EN LAPTOP: usa modo conversacional en stream con Ollama
# EN JETSON: ollama pull llama3.2:3b-instruct-fp16

import json
import httpx
import sys

OLLAMA_URL   = "http://localhost:11434/api/chat"
#direccion donde ollama escuchara 

# Selección automática del modelo optimizado
if sys.platform == "win32":
    OLLAMA_MODEL = "llama3.2:3b"
else:
    OLLAMA_MODEL = "llama3.2:3b-instruct-fp16"

async def verificar_ollama():
    """Verifica si Ollama está ejecutándose de forma asíncrona."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            resp.raise_for_status()
            return True
    except Exception as e:
        print(f"[LLM] ❌ Error al verificar Ollama: {e}")
        return False
# =========================================================================
# PARA MIGRACIÓN A JETSON (CUDA) - Clasificación de Tono
# =========================================================================
# SYSTEM_PROMPT_TONO = """
# Eres un clasificador de tono de conversación para un robot social.
# Analiza el contexto de los últimos mensajes y clasifica el tono emocional.
# 
# Responde ÚNICAMENTE con este JSON, sin texto extra:
# {"tono": "neutral"}
# {"tono": "happy"}
# {"tono": "angry"}
# 
# Reglas:
# - "happy"  → el usuario está contento, agradecido, emocionado, hace cumplidos.
# - "angry"  → el usuario está frustrado, molesto, usa palabras negativas o groserías.
# - "neutral"→ cualquier otra cosa: preguntas, conversación normal, saludos.
# """.strip()
# 
# TONO_A_VALOR = {
#     "neutral": "0",
#     "happy":   "1",
#     "angry":   "3"
# }
# 
# historial_tono = []  # guarda los ultimos 3 mensajes para tener contexto en la conversacion
# 
# async def clasificar_tono(texto: str) -> tuple[str, str]:   ###me da el tono para enviar a esp32
#     """
#     Retorna (tono, valor) ej: ("happy", "1")
#     Ejemplos:
#         - clasificar_tono("¡Qué bien! Me encanta") → ("happy", "1")
#         - clasificar_tono("Estoy enojado") → ("angry", "3")  
#         - clasificar_tono("¿Qué hora es?") → ("neutral", "0")
#     """
# 
#     historial_tono.append({"role": "user", "content": texto})
#     if len(historial_tono) > 6:  # 3 turnos = 6 mensajes (user+assistant)
#         historial_tono.pop(0)
# 
#     contexto = historial_tono[-6:]
# 
#     payload = {
#         "model":   OLLAMA_MODEL,    ##modelo a usar
#         "messages": [{"role": "system", "content": SYSTEM_PROMPT_TONO}] + contexto,
#                                     ##instrucciones del historial
#         "stream":  False,           ##respuesta en tiempo real
#         "options": {"temperature": 0.1, "num_predict": 30}
#     }
# 
#     try:
#         async with httpx.AsyncClient() as client:
#             resp.raise_for_status()
#             resp.raise_for_status()
#             contenido = resp.json()["message"]["content"].strip()
#             data  = json.loads(contenido)
#             tono  = data.get("tono", "neutral")
#     except Exception as e:
#         print(f"[LLM] Error en clasificar_tono: {e}")
#         tono = "neutral"
# 
#     # Validar que sea un valor permitido
#     if tono not in TONO_A_VALOR:
#         tono = "neutral"
# 
#     valor = TONO_A_VALOR[tono]
#     historial_tono.append({"role": "assistant", "content": f'{{"tono": "{tono}"}}'})
# 
#     print(f"[LLM] Tono={tono} | Valor={valor}")
#     return tono, valor
# =========================================================================

# --- NUEVA LÓGICA CONVERSACIONAL XAVI ---

SYSTEM_PROMPT_XAVI = "Eres XAVI, un asistente personal inteligente, elocuente y servicial. Responde siempre en español de forma directa y concisa para mantener la fluidez en una conversación por voz."

historial_xavi = []

async def conversar_xavi(texto: str):
    """
    Generador asíncrono que conecta con Ollama en stream.
    Libera el event loop de asyncio mientras espera tokens de la red.
    """
    # Verificar que Ollama esté disponible
    if not await verificar_ollama():
        yield " No puedo conectar con Ollama. Por favor, asegúrate de que esté ejecutándose."
        return
    
    historial_xavi.append({"role": "user", "content": texto})
    
    # Mantenemos un historial dinámico
    if len(historial_xavi) > 10:
        historial_xavi.pop(0)

    contexto = historial_xavi[-10:]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT_XAVI}] + contexto,
        "stream": True,
        "options": {"temperature": 0.5}
    }

    respuesta_completa = ""
    try:
        # Usamos el cliente asíncrono de httpx configurando el timeout para streaming
        timeout = httpx.Timeout(15.0, read=None)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                response.raise_for_status()
                
                # Iteramos las líneas de forma asíncrona sin bloquear el script principal
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            respuesta_completa += token
                            yield token
                            
                        if chunk.get("done"):
                            break
    except Exception as e:
        print(f"\n[LLM] Error en conversar_xavi: {e}")
        yield " Lo siento, experimenté un problema interno."
    
    if respuesta_completa:
        historial_xavi.append({"role": "assistant", "content": respuesta_completa.strip()})