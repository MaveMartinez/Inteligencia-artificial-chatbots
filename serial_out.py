# serial_out.py
# EN JETSON: pip install pyserial
# Conectar ESP32 con cable USB y verificar puerto con: ls /dev/ttyUSB*
# enviar numero para cargar ojos al esp32

import sys
import serial
import time

BAUDRATE = 115200

# Detección automática de plataforma
if sys.platform == "win32":
    PUERTO = 'COM3'  # Ajusta al número de COM de tu laptop
else:
    PUERTO = '/dev/ttyUSB0' # Puerto por defecto en Linux / Jetson

ser = None  # se inicializa al llamar conectar()

def conectar() -> bool:
    global ser
    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=1)
        time.sleep(2)  # ESP32 necesita ~2s para inicializarse tras conexión
        print(f"[SERIAL] Conectado en {PUERTO}")
        return True
    except Exception as e:
        print(f"[SERIAL] No se pudo conectar: {e}")
        return False

def enviar_a_ESP32(valor: str) -> None:
    """Envía el valor al ESP32. valor = '0', '1' o '3'"""
    if ser and ser.is_open:
        ser.write(f"{valor}\n".encode())
        print(f"[SERIAL] Enviado: {valor}")
    else:
        print(f"[SERIAL] Sin conexión. Valor que se enviaría: {valor}")

def cerrar() -> None:
    if ser and ser.is_open:
        ser.close()
        print("[SERIAL] Puerto cerrado.")