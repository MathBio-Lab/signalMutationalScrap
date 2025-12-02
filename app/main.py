import fastapi
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# routes
from app.api import upload
from app.api import check
from app.api import status
from app.celery.task.process_task import set_initial_tokens

app = fastapi.FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def on_app_startup():
    """
    Al iniciar la aplicación, inicializa los tokens en Redis de forma segura.
    """
    print("[INIT] Ejecutando inicialización de tokens en el startup de FastAPI...")
    await set_initial_tokens()


app.include_router(upload.router)
app.include_router(check.router)
app.include_router(status.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
