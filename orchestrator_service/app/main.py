from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

app = FastAPI(title="Orchestrator Service", version="1.0.0")

# Configuración CORS: Permite que el Frontend (Angular) hable con este servicio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200/"],  # En producción cambia esto por la URL real del front
    allow_credentials=True,
    allow_methods=["http://localhost:4200/"],
    allow_headers=["http://localhost:4200/"],
)

# Incluir las rutas
app.include_router(router)

@app.get("/")
def root():
    return {"status": "Orchestrator running", "services": ["parser", "analyzer"]}