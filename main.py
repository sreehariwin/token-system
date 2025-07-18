from fastapi import FastAPI
from config import engine

import tables.users as user_tables

import routes.users as user_routes

user_tables.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user_routes.router)

# @app.get("/")
# async def root():
#     return {"message": "Hello World"}