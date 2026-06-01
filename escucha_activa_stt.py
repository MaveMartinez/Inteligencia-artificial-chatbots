# stt.py
# EN LAPTOP: usa Vosk (optimizado para CPU)
# EN JETSON: usa faster-whisper

import os
import numpy as np
import sounddevice as sd
import sys
import json

# PARA MIGRACIÓN A JETSON (CUDA)
# from faster_whisper import WhisperModel

if sys.platform == "win32":
    from vosk import Model, KaldiRecognizer

SAMPLE_RATE    = 16000   ###la inversa sera la duracion de una muestra
BLOCK_SIZE     = 4096
SILENCE_SECS   = 1.8     ###tiempo en segundos de silencio
VAD_THRESHOLD  = 0.0005  
MAX_SECS       = 15

# Configuración automática dependiendo de la máquina
if sys.platform == "win32":
    # Configuración óptima para tu laptop (CPU)
    model_paths = [
        "vosk-model-small-es",
        "vosk-model-small-es-0.42",
        "vosk-model-small-es-0.42-2023",
    ]
    model_path = next((p for p in model_paths if os.path.isdir(p)), None)
    if model_path is None:
        model_path = "vosk-model-small-es"

    try:
        vosk_model = Model(model_path)
        recognizer = KaldiRecognizer(vosk_model, SAMPLE_RATE)
        print(f"[STT] ✅ Modelo Vosk cargado desde: {model_path}")
    except Exception as e:
        print(f"[STT] ❌ Error cargando Vosk desde '{model_path}': {e}")
        print(f"[STT] Asegúrate de tener la carpeta 'vosk-model-small-es-0.42' en: {os.getcwd()}")
else:
    # PARA MIGRACIÓN A JETSON (CUDA)
    # model = WhisperModel("tiny", device="cuda", compute_type="float16")
    pass

def grabar_hasta_silencio() -> np.ndarray:
    chunks = []                  
    ###lista para grabar los trozos de audio que se van grabando
    silence_frames = int(SAMPLE_RATE * SILENCE_SECS / BLOCK_SIZE) 
    ###bloques de silencio necesarios para considerar que termino la grabacion
    max_frames     = int(SAMPLE_RATE * MAX_SECS / BLOCK_SIZE) 
    ###limite maximo de tiempo grabando
    silent_count   = 0                        
    ###contador de bloques de silencio consecutivos
    grabando       = False

    print("[STT] Escuchando...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        dtype="float32", blocksize=BLOCK_SIZE) as stream:
        for _ in range(max_frames):
            chunk, _ = stream.read(BLOCK_SIZE)    ###bloque de audio de tamaño block_size*(1/sample_rate)
            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if rms > VAD_THRESHOLD:
                grabando = True
                silent_count = 0
                chunks.append(chunk.copy())
            elif grabando:
                chunks.append(chunk.copy())
                silent_count += 1
                if silent_count >= silence_frames:
                    break

    if not chunks:      ###si no hay audio grabado, devuelve un array de ceros para evitar errores en la trama
        return np.zeros(BLOCK_SIZE, dtype="float32") ###da ceros al block size
    return np.concatenate(chunks, axis=0).flatten()  ###da todo el audio junto

def escuchar() -> str:
    audio = grabar_hasta_silencio()  ###en audio se almacena la grabacion
    
    if sys.platform == "win32":
        # Conversión de float32 a int16 (PCM) requerido por Vosk
        audio_int16 = (audio * 32767).astype(np.int16)
        recognizer.AcceptWaveform(audio_int16.tobytes())
        resultado = json.loads(recognizer.FinalResult())
        texto = resultado.get("text", "").strip()
        print(f"[STT] Transcripción (Vosk): '{texto}'")
        return texto
    else:
        # PARA MIGRACIÓN A JETSON (CUDA)
        # segments, _ = model.transcribe(  ###MODELO TTS
        #     audio,               ###carga la grabacion
        #     language="es",
        #     vad_filter=True,
        #     vad_parameters={"min_silence_duration_ms": 500}  ###separa frases cada 0.5 segundos de silencio
        # )     
        # texto = " ".join(s.text for s in segments).strip()  ###une las frases y las une en un solo texto
        # print(f"[STT] Transcripción (Whisper): '{texto}'")   ####imprime en consola, el texto detectado
        # return texto
        return ""