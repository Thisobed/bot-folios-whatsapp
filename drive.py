"""
Conexión a Google Drive: descarga el archivo Excel más reciente de la
carpeta compartida con la cuenta de servicio.
"""
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ID de la carpeta de Drive (se saca de la URL: drive.google.com/drive/folders/<ESTE_ID>)
FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")

# El JSON de la cuenta de servicio se guarda como variable de entorno
# (contenido completo del archivo .json, no la ruta)
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")


def _get_service():
    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def descargar_export_mas_reciente(destino_local="/tmp/ultimo_export.xlsx"):
    """
    Busca el archivo .xlsx más reciente en la carpeta configurada,
    lo descarga a destino_local y regresa la ruta.
    """
    service = _get_service()

    resultados = service.files().list(
        q=f"'{FOLDER_ID}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed=false",
        orderBy="modifiedTime desc",
        pageSize=1,
        fields="files(id, name, modifiedTime)",
    ).execute()

    archivos = resultados.get("files", [])
    if not archivos:
        raise FileNotFoundError("No se encontró ningún .xlsx en la carpeta de Drive configurada.")

    archivo = archivos[0]
    request = service.files().get_media(fileId=archivo["id"])
    fh = io.FileIO(destino_local, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.close()

    return destino_local, archivo["name"], archivo["modifiedTime"]


if __name__ == "__main__":
    ruta, nombre, modificado = descargar_export_mas_reciente()
    print(f"Descargado: {nombre} (modificado: {modificado}) -> {ruta}")
