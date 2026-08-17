"""
Servidor del bot de WhatsApp para estatus de folios.

Flujo:
1. Cada N minutos (hilo en segundo plano) descarga el export más reciente
   de Google Drive y lo carga en memoria.
2. Twilio manda un POST a /whatsapp cada vez que alguien escribe al bot.
3. Se extrae el número de folio del mensaje, se busca en los datos en
   memoria, y se contesta con el estatus formateado.
"""
import os
import re
import threading
import time
import logging

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from parser import cargar_folios, formatear_respuesta
from drive import descargar_export_mas_reciente

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot-folios")

app = Flask(__name__)

# --- Estado en memoria compartido entre el hilo de actualización y las peticiones web ---
_estado = {"folios": {}, "ultima_actualizacion": None, "archivo_origen": None}
_lock = threading.Lock()

INTERVALO_ACTUALIZACION_SEGUNDOS = int(os.environ.get("INTERVALO_ACTUALIZACION_SEGUNDOS", "1800"))  # 30 min por default


def actualizar_datos():
    """Descarga el export más reciente de Drive y recarga los folios en memoria."""
    try:
        ruta, nombre, modificado = descargar_export_mas_reciente()
        folios = cargar_folios(ruta)
        with _lock:
            _estado["folios"] = folios
            _estado["ultima_actualizacion"] = time.strftime("%d/%m %H:%M")
            _estado["archivo_origen"] = nombre
        log.info(f"Datos actualizados: {len(folios)} folios cargados desde '{nombre}'")
    except Exception as e:
        log.error(f"Error actualizando datos desde Drive: {e}")


def hilo_actualizacion_periodica():
    while True:
        actualizar_datos()
        time.sleep(INTERVALO_ACTUALIZACION_SEGUNDOS)


def extraer_folio(texto_mensaje):
    """Extrae el número de folio de un mensaje tipo 'estatus 20288410' o solo '20288410'."""
    match = re.search(r"\d{5,}", texto_mensaje)
    return match.group(0) if match else None


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    mensaje_entrante = request.values.get("Body", "").strip()
    folio = extraer_folio(mensaje_entrante)

    resp = MessagingResponse()

    if not folio:
        resp.message(
            "Escríbeme el número de folio para darte su estatus.\n"
            "Ejemplo: *estatus 20288410*"
        )
        return str(resp)

    with _lock:
        folio_data = _estado["folios"].get(folio)

    texto_respuesta = formatear_respuesta(folio_data)
    resp.message(texto_respuesta)
    return str(resp)


@app.route("/status", methods=["GET"])
def status():
    """Endpoint simple para confirmar que el servidor está vivo y ver cuándo actualizó datos."""
    with _lock:
        return {
            "folios_cargados": len(_estado["folios"]),
            "ultima_actualizacion": _estado["ultima_actualizacion"],
            "archivo_origen": _estado["archivo_origen"],
        }


# --- Arranque del refresco de datos ---
# Esto corre siempre al importar el módulo (tanto con gunicorn en Render
# como al ejecutar "python app.py" en local), para que la primera carga
# y el hilo de actualización periódica no dependan de cómo se inicie el servidor.
actualizar_datos()
hilo = threading.Thread(target=hilo_actualizacion_periodica, daemon=True)
hilo.start()


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=puerto)
