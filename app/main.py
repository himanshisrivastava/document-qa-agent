# from dotenv import load_dotenv
from fastapi import FastAPI
from app.routes.document_qa import router as documents_router

# load_dotenv()

def create_app() -> FastAPI:
    application = FastAPI(title="Document Q&A Agent")
    application.include_router(documents_router)
    return application

app = create_app()
