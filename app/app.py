from fastapi import FastAPI

from app.api.routes.files_routes import FileRoutes
app = FastAPI()

file_routes = FileRoutes()

app.include_router(file_routes.router)
