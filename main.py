from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
import auth
import analyze
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# MongoDB Connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/batch25")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.get_database() # This will use the DB from the URL or default
users_collection = db.users

# --- CORS SETTINGS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin for origin in [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            os.getenv("FRONTEND_URL", ""),
        ] if origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)

async def get_users_collection():
    return users_collection

async def get_current_user(
    token: str = Depends(auth.oauth2_scheme),
    collection = Depends(get_users_collection)
):
    return await auth.get_current_user_from_db(token, collection)

@app.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user(
    user: auth.UserCreate,
    collection = Depends(get_users_collection)
):
    existing_user = await auth.get_user(collection, user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.pwd_context.hash(user.password)
    new_user = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password
    }
    await collection.insert_one(new_user)
    return {"message": "User created successfully"}

@app.post("/login", response_model=auth.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    collection = Depends(get_users_collection)
):
    user = await auth.get_user(collection, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=auth.User)
async def read_users_me(current_user: auth.User = Depends(get_current_user)):
    return current_user