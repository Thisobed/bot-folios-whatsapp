# Bot de WhatsApp — Estatus de Folios

## Qué hace
Alguien escribe por WhatsApp "estatus 20288410" y el bot contesta con el
estatus actual de ese folio, leyendo los datos desde un Excel de DeltaX
que se actualiza automáticamente desde Google Drive.

## Archivos
- `parser.py` — lee el Excel y calcula el estatus de cada folio
- `drive.py` — descarga el export más reciente de tu carpeta de Google Drive
- `app.py` — servidor que recibe los mensajes de WhatsApp (vía Twilio) y contesta
- `requirements.txt` — librerías necesarias

## Cómo desplegarlo (sin programar)

### 1. Sube estos archivos a GitHub
1. Ve a github.com → botón verde "New" (crear repositorio)
2. Nómbralo, por ejemplo, `bot-folios-whatsapp`
3. Arrastra estos 5 archivos (parser.py, drive.py, app.py, requirements.txt, README.md) a la página del repositorio y confirma el commit

### 2. Consigue el ID de tu carpeta de Drive
Abre tu carpeta de Drive en el navegador. La URL se ve así:
```
https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
```
El ID es la parte después de `/folders/` (en el ejemplo: `1AbCdEfGhIjKlMnOpQrStUvWxYz`). Guárdalo, lo vas a necesitar.

### 3. Crea el servicio en Render
1. En render.com → "New +" → "Web Service"
2. Conecta el repositorio de GitHub que acabas de crear
3. Configuración:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. **No le des "Create" todavía** — primero baja a "Environment Variables" y agrega estas (sección "Advanced" o "Environment"):

| Variable | Valor |
|---|---|
| `DRIVE_FOLDER_ID` | el ID que sacaste en el paso 2 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | el **contenido completo** del archivo .json que descargaste de Google Cloud (ábrelo con el Bloc de notas, copia todo, pégalo aquí) |
| `TWILIO_ACCOUNT_SID` | tu Account SID de Twilio |
| `TWILIO_AUTH_TOKEN` | tu Auth Token de Twilio |

5. Ahora sí, dale "Create Web Service". Va a tardar unos minutos en desplegar.
6. Cuando termine, Render te da una URL tipo `https://bot-folios-whatsapp.onrender.com`

### 4. Conecta esa URL a Twilio
1. En Twilio, ve a Messaging → Try it out → Send a WhatsApp message → busca la configuración del Sandbox (ícono de engrane / "Sandbox settings")
2. En el campo **"WHEN A MESSAGE COMES IN"**, pega tu URL de Render + `/whatsapp`, por ejemplo:
   ```
   https://bot-folios-whatsapp.onrender.com/whatsapp
   ```
3. Método: **HTTP POST**
4. Guarda

### 5. Pruébalo
Escríbele por WhatsApp al número del sandbox de Twilio: `estatus 20288410` (o cualquier folio real). Debería contestarte en unos segundos (la primera vez puede tardar ~30-50 seg si el servicio "estaba dormido").

Para confirmar que el servidor está vivo y ver cuándo actualizó datos por última vez, visita en el navegador:
```
https://bot-folios-whatsapp.onrender.com/status
```

## Notas
- El bot revisa la carpeta de Drive cada 30 minutos por default (se puede ajustar con la variable `INTERVALO_ACTUALIZACION_SEGUNDOS`, en segundos)
- Solo detecta el archivo `.xlsx` más reciente de la carpeta — puedes seguir subiendo el export ahí cada vez, con cualquier nombre
- Nunca compartas el archivo .json ni el Auth Token de Twilio fuera de las variables de entorno de Render
