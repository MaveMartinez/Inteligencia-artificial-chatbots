#!/usr/bin/env python3
"""
Script de diagnóstico para probar Piper + ffplay
Ejecuta: python test_audio.py
"""

import os
import sys
import asyncio
import shutil

async def test_audio_con_texto(texto):
    """Prueba con un texto específico"""
    piper_local = os.path.join(os.getcwd(), "piper.exe")
    piper_bin = piper_local if os.path.exists(piper_local) else shutil.which("piper") or "piper"
    ffplay_bin = shutil.which("ffplay") or "ffplay"
    
    # Limpiar el texto
    texto_limpio = texto.replace('"', '').replace("'", "").replace('\n', ' ')
    
    # --length-scale 1.5 hace que hable 1.5x más lento (default es 1.0)
    cmd = (
        f'echo "{texto_limpio}" | "{piper_bin}" --model es_ES-davefx-medium.onnx --length-scale 1.5 --output_raw '
        f'| "{ffplay_bin}" -loglevel quiet -autoexit -nodisp -f s16le -ar 22050 -'
    )
    
    try:
        proceso = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proceso.communicate()
        
        if proceso.returncode != 0:
            print(f"    ❌ Error (código {proceso.returncode})")
            if stderr:
                print(f"    stderr: {stderr.decode()[:100]}")
        else:
            print(f"    ✅ Reproducido correctamente")
    except Exception as e:
        print(f"    ❌ Error: {e}")

async def test_audio():
    """Prueba simple de reproducción de audio"""
    
    print("\n" + "="*60)
    print("🔊 PRUEBA DE AUDIO - XAVI")
    print("="*60 + "\n")
    
    # 1. Verificar piper
    print("[1/3] Buscando Piper...")
    piper_local = os.path.join(os.getcwd(), "piper.exe")
    piper_bin = piper_local if os.path.exists(piper_local) else shutil.which("piper")
    
    if not piper_bin or not os.path.exists(piper_bin):
        print("❌ Piper no encontrado")
        return
    
    print(f"✅ Piper encontrado: {piper_bin}\n")
    
    # 2. Verificar ffplay
    print("[2/3] Buscando ffplay...")
    ffplay_bin = shutil.which("ffplay")
    if not ffplay_bin:
        ffplay_bin = "ffplay"  # Intentar sin ruta
    
    print(f"✅ ffplay configurado: {ffplay_bin}\n")
    
    # 3. Probar reproducción
    print("[3/3] Reproduciendo prueba de audio...")
    print("💬 Deberías escuchar: 'Hola, estoy funcionando'\n")
    
    texto = "Hola, estoy funcionando"
    cmd = (
        f'echo "{texto}" | "{piper_bin}" --model es_ES-davefx-medium.onnx --length-scale 1.5 --output_raw '
        f'| "{ffplay_bin}" -loglevel quiet -autoexit -nodisp -f s16le -ar 22050 -'
    )
    
    print(f"Comando ejecutado:\n{cmd}\n")
    
    try:
        proceso = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proceso.communicate()
        
        if proceso.returncode != 0:
            print(f"❌ Error en ffplay (código {proceso.returncode})")
            if stderr:
                print(f"stderr: {stderr.decode()}")
        else:
            print("✅ Audio reproducido sin errores\n")
    
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    print("="*60)
    print("DIAGNÓSTICO COMPLETADO")
    print("="*60 + "\n")
    
    print("Si NO escuchaste el audio, verifica:")
    print("  ✓ El volumen del sistema está AL MÁXIMO")
    print("  ✓ Los altavoces están físicamente conectados")
    print("  ✓ No hay otra app reproduciendo audio")
    print("  ✓ El dispositivo de audio predeterminado es correcto\n")
    print("Prueba manualmente:")
    print("  powershell -Command \"[console]::beep(440, 500)\"  # Debería sonar un beep\n")

if __name__ == "__main__":
    asyncio.run(test_audio())
    
    # Prueba adicional con textos reales más largos
    print("\n" + "="*60)
    print("🎤 PRUEBA CON TEXTOS REALES")
    print("="*60 + "\n")
    
    textos_prueba = [
        "Hola, soy XAVI tu asistente personal.",
        "Estoy aquí para ayudarte en lo que necesites.",
        "¿Cómo estás hoy? Me gustaría charlar contigo sobre tus planes.",
        "La inteligencia artificial y la voz sintetizada funcionan perfectamente en tu máquina.",
    ]
    
    print("Reproduciendo textos de prueba...\n")
    for i, texto in enumerate(textos_prueba, 1):
        print(f"[{i}] Reproduciendo: \"{texto}\"")
        asyncio.run(test_audio_con_texto(texto))
        print()
    
    print("="*60)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*60 + "\n")
