# main.py
# Loop principal asíncrono: voz → Ollama → TTS Asíncrono

import os
import shutil
import sys
import asyncio
from escucha_activa_stt import escuchar
from llamas import conversar_xavi
from serial_out import conectar, enviar_a_ESP32, cerrar

# PARA MIGRACIÓN A JETSON (CUDA)
# from llamas import clasificar_tono

cola_audio = asyncio.Queue()

def verificar_dependencias_audio():
    """Verifica que Piper y ffplay estén disponibles"""
    # Buscar piper primero en el directorio local, luego en el PATH
    piper_local = os.path.join(os.getcwd(), "piper.exe")
    piper_bin = piper_local if os.path.exists(piper_local) else shutil.which("piper")
    
    ffplay_bin = shutil.which("ffplay") or "ffplay"
    
    if not piper_bin or not os.path.exists(piper_bin):
        print("[AUDIO] ❌ Piper no encontrado")
        return False
    
    print(f"[AUDIO] ✅ Piper encontrado: {piper_bin}")
    return True

async def probar_audio():
    """
    Función de diagnóstico: prueba que el audio está funcionando
    """
    print("\n[AUDIO] 🔊 Iniciando prueba de audio...")
    print("[AUDIO] Deberías escuchar: 'Hola, estoy funcionando'")
    
    await reproducir_audio("Hola, estoy funcionando")
    
    print("[AUDIO] ✅ Prueba completada")
    print("[AUDIO] Si no escuchaste nada, verifica:")
    print("[AUDIO]   - El volumen del sistema está al máximo")
    print("[AUDIO]   - Los altavoces están conectados")
    print("[AUDIO]   - El micrófono no está silenciado")
    print("[AUDIO]\n")

async def reproducir_audio(texto: str):
    texto_limpio = (
        texto.replace('"', '')
        .replace("'", "")
        .replace('\n', ' ')
        .replace('¿', '')
        .replace('?', '')
        .replace('¡', '')
        .replace('!', '')
        .replace('á', 'a')
        .replace('é', 'e')
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('ú', 'u')
        .replace('ñ', 'n')
    )
    #busca las rutas el folder de proyecto
    piper_local = os.path.join(os.getcwd(), "piper.exe")
    piper_bin = piper_local if os.path.exists(piper_local) else shutil.which("piper") or "piper"
    #verifica la carpeta, el path, y el comando nativo del sistema
    
    ffplay_bin = shutil.which("ffplay") or "ffplay"
    modelo_onnx = os.path.join(os.getcwd(), "es_ES-davefx-medium.onnx")
    
    #crea subprocesos de consola cmd_piper y cmd_ffplay
    #subproceso: le pide al sistema operativo que abra 
    #otro programa en celdas de memorias independientes

    #Pipes de comunicacion: stdin, stdout, stderr
    #
    cmd_piper = f'"{piper_bin}" --model "{modelo_onnx}" --length-scale 1.3 --output_raw'
    cmd_ffplay = f'"{ffplay_bin}" -loglevel quiet -autoexit -nodisp -f s16le -ar 22050 -'
    try:
        p_piper = await asyncio.create_subprocess_shell(
            cmd_piper,
            #abro 3 tuberias para introducir
            #extraer audio y capturar errores ocultos.
            stdin   = asyncio.subprocess.PIPE,
            stdout  = asyncio.subprocess.PIPE,
            stderr  = asyncio.subprocess.PIPE
        )
        #inyecta la frase en bytes de audio, a stdout. Durante
        #el await, se hace la conversion y al stdout solo 
        #llegan bytes, ondas sonoras digitales.
        stdout_piper, stderr_piper = await p_piper.communicate(input=texto_limpio.encode('cp1252', errors='ignore')) 

        bytes_calculados = len(stdout_piper)
        print(f"[PIPER AUDIO RAW] Texto procesado: '{texto_limpio}' | Content-Length: {bytes_calculados} bytes.")       

        if stderr_piper and bytes_calculados == 0:
            print(f"[⚠️ ALERTA DE SISTEMA - FIN DE PROCESO]: {stderr_piper.decode(errors='ignore').strip()}")
        # 3. Si Piper generó audio, se lo pasamos directamente a FFplay por su stdin
        if stdout_piper and bytes_calculados > 0:
            p_ffplay = await asyncio.create_subprocess_shell(
            cmd_ffplay,
            stdin   = asyncio.subprocess.PIPE, #tuberia de entrada para stdin
            stdout  = asyncio.subprocess.DEVNULL,
            stderr  = asyncio.subprocess.DEVNULL
            )
            #cada que veo stdin, stdout o stderr
            #se configura el destino de las 3 puertas
            #predeterminadas del nuevo subproceso

            # Le entregamos el buffer de audio a ffplay y esperamos que termine de sonar
            await p_ffplay.communicate(input=stdout_piper)
        else:
            print("[⚠️ ADVERTENCIA] La manguera de datos está vacía. Saltando inicialización de FFplay.")
    except Exception as e:
        print(f"[AUDIO] No se pudo reproducir por error en la tubería asíncrona: {e}")
        
async def worker_audio():
    while True:
        texto = await cola_audio.get() #espera una frase
        if texto is None:
            break
        print(f"\n[ENTREGA TTS] 📦 Saliendo de la cola hacia Piper TTS: '{texto}'")
        await reproducir_audio(texto)
        cola_audio.task_done()
        #saca las cajas de texto en orden de llegada y 
        #las pasa a la funcion encargada de la fabrica
        #de sonido

async def procesar_conversacion():
    # Verificar dependencias de audio primero
    if not verificar_dependencias_audio():
        return
    
    # Iniciamos el worker encargado de reproducir las oraciones asíncronamente
    tarea_worker = asyncio.create_task(worker_audio())

    try:
        while True:
            # 1. Escuchar por voz (Se lanza a un thread para no bloquear asyncio)
            print("\n[MAIN] Esperando a que hables...")
            texto = await asyncio.to_thread(escuchar)

            if not texto:
                continue

            print(f"[MAIN] Tú: {texto}")

            # =========================================================
            # PARA MIGRACIÓN A JETSON (CUDA)
            # tono, valor = clasificar_tono(texto)
            # enviar_a_ESP32(valor)
            # =========================================================

            print("[MAIN] XAVI: ", end="", flush=True)
            
            oracion_actual = ""
            
            # 2. Enviar a conversar_xavi y recibir tokens en streaming
            async for token in conversar_xavi(texto):
                print(token, end="", flush=True)
                oracion_actual += token
                
                # 3. Segmentar texto por oraciones para enviarlas inmediatamente a Piper TTS
                if any(puntuacion in token for puntuacion in ['.', '!', '?']):
                    if oracion_actual.strip():
                        # Encolamos la oración para que se vaya reproduciendo en el subproceso
                        await cola_audio.put(oracion_actual.strip())
                        oracion_actual = ""
                
                # Ceder el control brevemente para permitir que el worker de audio y
                # el subproceso asíncrono de shell comiencen la reproducción en tiempo real.
                await asyncio.sleep(0.01)
            
            # Si sobró alguna oración sin puntuación al final
            if oracion_actual.strip():
                await cola_audio.put(oracion_actual.strip())

            # Esperamos a que la cola termine de hablar toda la respuesta antes de volver a escuchar
            await cola_audio.join()

    finally:
        await cola_audio.put(None)
        await tarea_worker

async def main_async():
    conectar()

    print("=" * 40)
    print("  XAVI — Modo Conversacional Asíncrono (Vosk + Ollama + Piper)")
    print("  Habla para comenzar. Ctrl+C para salir.")
    print("=" * 40)

    try:
        await procesar_conversacion()
    except KeyboardInterrupt:
        print("\n[MAIN] Detenido por el usuario.")
    finally:
        cerrar()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass