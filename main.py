from fastapi import FastAPI, HTTPException, Request
from supabase import create_client, Client
import httpx
import os

app = FastAPI()

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Configuración de Supabase (obtenida de variables de entorno)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Las variables de entorno SUPABASE_URL y SUPABASE_KEY deben estar definidas.")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    # Captura errores durante la inicialización del cliente Supabase
    print(f"Error al inicializar el cliente Supabase: {e}")
    raise ValueError(f"Error al conectar con Supabase: {e}")

# Log para verificar la inicialización y las variables leídas
print(f"Supabase URL leída: {SUPABASE_URL}")
print(f"Supabase Key leída: {'*' * (len(SUPABASE_KEY) - 5) + SUPABASE_KEY[-5:] if SUPABASE_KEY else 'None'}") # Ocultar la mayor parte de la key
print(f"Cliente Supabase inicializado: {supabase is not None}")


@app.get("/ping")
async def ping():
    return {"message": "pong"}

from fastapi import Body
import string
import random
from datetime import datetime

# Endpoint para acortar URL
@app.post("/shorten")
async def shorten_url(data: dict = Body(...)):
    original_url = data.get("url")
    if not original_url:
        raise HTTPException(status_code=400, detail="URL no proporcionada")

    # Generar código corto único
    code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    try:
        # Verificar unicidad en Supabase
        existing = supabase.table("links").select("id").eq("short_code", code).execute()
        while existing.data:
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            existing = supabase.table("links").select("id").eq("short_code", code).execute()

        # Guardar en Supabase
        insert_result = supabase.table("links").insert({
            "original_url": original_url,
            "short_code": code,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Opcional: Verificar si hubo error en la respuesta de Supabase
        # if hasattr(insert_result, 'error') and insert_result.error:
        #     print(f"Error Supabase al interactuar: {insert_result.error.message}")
        #     raise HTTPException(status_code=500, detail=f"Error Supabase al guardar: {insert_result.error.message}")

    except Exception as e:
        # Captura cualquier excepción durante la interacción con Supabase
        print(f"Error al interactuar con Supabase en /shorten: {e}") # Log para Railway
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al procesar el enlace: {e}")

    # Construir la URL acortada usando la URL base de la solicitud actual
    # Esto es mejor que hardcodear localhost
    # Necesitamos el objeto Request para obtener base_url
    # Modificar la firma de la función para incluir request: Request
    # async def shorten_url(request: Request, data: dict = Body(...)):
    # base_url = str(request.base_url)
    # short_url = f"{base_url}{code}"
    # Por ahora, mantenemos localhost hasta ajustar la firma si es necesario
    short_url = f"http://localhost:8000/{code}" # Temporal, idealmente usar request.base_url

    return {"short_url": short_url}

from fastapi.responses import RedirectResponse

# Endpoint para redirigir y registrar visita
@app.get("/{code}")
async def redirect_and_log(code: str, request: Request):
    # Buscar URL original
    result = supabase.table("links").select("*").eq("short_code", code).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Enlace no encontrado")

    link = result.data[0]
    original_url = link["original_url"]

    # Obtener datos del visitante
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "desconocido")
    fecha = datetime.utcnow().isoformat()

    # Obtener ubicación usando ip-api.com
    location = {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}")
            if resp.status_code == 200:
                location = resp.json()
    except:
        location = {}

    # Guardar visita en Supabase
    supabase.table("visits").insert({
        "link_id": link["id"],
        "ip": ip,
        "user_agent": user_agent,
        "location": location,
        "visited_at": fecha
    }).execute()

    # Redirigir al usuario
    return RedirectResponse(original_url)

# Endpoint para obtener visitas de un enlace
@app.get("/visits/{code}")
async def get_visits(code: str):
    # Buscar enlace
    result = supabase.table("links").select("id").eq("short_code", code).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Enlace no encontrado")

    link_id = result.data[0]["id"]

    # Obtener visitas relacionadas
    visits_result = supabase.table("visits").select("*").eq("link_id", link_id).execute()

    return {"visits": visits_result.data}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
