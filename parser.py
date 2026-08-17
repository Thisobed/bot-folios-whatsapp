"""
Parser del export "Órdenes de carga" de DeltaX.
Lee el Excel, calcula el estatus de cada folio (incluyendo cargando/descargando
derivado de columnas de tiempo) y arma la respuesta de texto para WhatsApp.
"""
import openpyxl
from datetime import datetime

# Índices de columnas relevantes (fila de encabezado = fila 3 del Excel)
COL = {
    "folio": 0,
    "descripcion_ruta": 3,
    "origen": 5,
    "destino": 7,
    "estado_folio": 11,
    "eta_origen": 15,
    "estado_eta_origen": 16,
    "llegada_origen": 19,
    "ingreso_origen": 20,
    "salida_origen": 21,
    "eta_destino": 28,
    "estado_eta_destino": 29,
    "llegada_destino": 32,
    "ingreso_destino": 33,
    "salida_destino": 34,
    "resultado_viaje": 42,
    "subestado_folio": 44,
    "operador": 58,
    "nro_incidencias": 66,
}

HEADER_ROW = 3
DATA_START_ROW = 4


def _parse_dt(valor):
    """
    DeltaX exporta las fechas como texto 'dd/mm/aaaa HH:MM:SS' (a veces ya
    vienen como datetime real si Excel las reconoció). Normaliza a datetime.
    """
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, str):
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.strptime(valor.strip(), fmt)
            except ValueError:
                continue
    return None


def _fmt(dt):
    """Formatea fecha/hora para mostrar en WhatsApp, o '' si está vacío."""
    dt = _parse_dt(dt)
    if dt is None:
        return ""
    return dt.strftime("%d/%m %H:%M")


def _hrs_desde(dt):
    """Horas transcurridas desde una fecha/hora hasta ahora."""
    dt = _parse_dt(dt)
    if dt is None:
        return None
    delta = datetime.now() - dt
    return round(delta.total_seconds() / 3600, 1)


def cargar_folios(ruta_excel):
    """
    Lee el Excel y regresa un dict {folio: {datos...}} con toda la info
    y el estatus derivado ya calculado.
    """
    wb = openpyxl.load_workbook(ruta_excel, data_only=True)
    ws = wb.active
    folios = {}

    for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
        if row[COL["folio"]] is None:
            continue

        folio = str(row[COL["folio"]])
        ingreso_origen = row[COL["ingreso_origen"]]
        salida_origen = row[COL["salida_origen"]]
        ingreso_destino = row[COL["ingreso_destino"]]
        salida_destino = row[COL["salida_destino"]]

        # --- Lógica de estatus derivado (cargando / descargando) ---
        tiene_ingreso_origen = _parse_dt(ingreso_origen) is not None
        tiene_salida_origen = _parse_dt(salida_origen) is not None
        tiene_ingreso_destino = _parse_dt(ingreso_destino) is not None
        tiene_salida_destino = _parse_dt(salida_destino) is not None

        if tiene_ingreso_origen and not tiene_salida_origen:
            estatus_derivado = "cargando_origen"
        elif tiene_ingreso_destino and not tiene_salida_destino:
            estatus_derivado = "descargando_destino"
        else:
            estatus_derivado = None

        folios[folio] = {
            "folio": folio,
            "descripcion_ruta": row[COL["descripcion_ruta"]],
            "origen": row[COL["origen"]],
            "destino": row[COL["destino"]],
            "estado_folio": row[COL["estado_folio"]],
            "subestado_folio": row[COL["subestado_folio"]],
            "eta_origen": row[COL["eta_origen"]],
            "estado_eta_origen": row[COL["estado_eta_origen"]],
            "eta_destino": row[COL["eta_destino"]],
            "estado_eta_destino": row[COL["estado_eta_destino"]],
            "ingreso_origen": ingreso_origen,
            "salida_origen": salida_origen,
            "ingreso_destino": ingreso_destino,
            "salida_destino": salida_destino,
            "resultado_viaje": row[COL["resultado_viaje"]],
            "operador": row[COL["operador"]],
            "nro_incidencias": row[COL["nro_incidencias"]],
            "estatus_derivado": estatus_derivado,
        }

    return folios


def formatear_respuesta(folio_data):
    """Arma el texto de respuesta de WhatsApp para un folio."""
    if folio_data is None:
        return ("No encontré ese folio en los últimos 4 días. "
                "Verifica el número e intenta de nuevo.")

    f = folio_data
    lineas = [f"*Folio {f['folio']}* — {f['origen']} → {f['destino']}"]

    # Estatus principal: prioriza el derivado (cargando/descargando) si aplica
    if f["estatus_derivado"] == "cargando_origen":
        hrs = _hrs_desde(f["ingreso_origen"])
        lineas.append(f"Estado: Cargando en origen (desde {_fmt(f['ingreso_origen'])})")
        if hrs is not None:
            lineas.append(f"Tiempo en origen: {hrs} hrs y contando")
    elif f["estatus_derivado"] == "descargando_destino":
        hrs = _hrs_desde(f["ingreso_destino"])
        lineas.append(f"Estado: Descargando en destino (desde {_fmt(f['ingreso_destino'])})")
        if hrs is not None:
            lineas.append(f"Tiempo en destino: {hrs} hrs y contando")
    else:
        lineas.append(f"Estado: {f['estado_folio']}"
                       + (f" ({f['subestado_folio']})" if f["subestado_folio"] else ""))

    # ETA destino si el viaje sigue en curso
    if f["eta_destino"] and not f["salida_destino"]:
        eta_txt = f"ETA destino: {_fmt(f['eta_destino'])}"
        if f["estado_eta_destino"]:
            eta_txt += f" ({f['estado_eta_destino']})"
        lineas.append(eta_txt)

    if f["resultado_viaje"]:
        lineas.append(f"Resultado: {f['resultado_viaje']}")

    if f["operador"]:
        lineas.append(f"Operador: {f['operador']}")

    if f["nro_incidencias"]:
        lineas.append(f"⚠️ Incidencias registradas: {f['nro_incidencias']}")

    lineas.append(f"_Última actualización: {datetime.now().strftime('%d/%m %H:%M')}_")

    return "\n".join(lineas)


if __name__ == "__main__":
    # Prueba rápida con el archivo de ejemplo
    import sys
    ruta = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/Órdenes_de_carga_-_1786990156673.xlsx"
    folios = cargar_folios(ruta)
    print(f"Folios cargados: {len(folios)}")
    primer_folio = next(iter(folios))
    print("\n--- Ejemplo de respuesta ---")
    print(formatear_respuesta(folios[primer_folio]))
