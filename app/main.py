from fastapi import FastAPI
from app.routes import chat, perfil, session
from app.config import validar_config
from fastapi.middleware.cors import CORSMiddleware
from app.config import FRONTEND_DIR


# VERIFICAÇÃO DE ERROS
for _problema in validar_config():                 # logo antes de app = FastAPI(...)
    print(f"[config] ATENÇÃO: {_problema}")

app = FastAPI(
    title = "AssessorIA",
    description = "Assessor financeiro com LangChain e LangGraph",
    version = "0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict:
    problemas = validar_config()
    return {
        "status": "ok" if not problemas else "atencao",
        "problemas_de_configuracao": problemas,
    }

app.include_router(chat.router)
app.include_router(session.router)
app.include_router(perfil.router)

if (FRONTEND_DIR / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
 
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {"message": "Frontend not found. Please build the frontend and place it in the 'frontend' directory."}
