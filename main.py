from typing import Union, List, Optional, Annotated
from db_work import database
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Depends, Query
from fastapi import Body, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from db_work.models import User
from fastapi import Path
from routers.auth import router as auth_router, get_current_user, oauth2_scheme
from routers.llm import router as llm_router
from routers.exercise import router as ex_router
from routers.goal import router as goal_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(llm_router)
app.include_router(ex_router)
app.include_router(goal_router)

@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }


@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}
