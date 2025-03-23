from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from pydantic import BaseModel
import logging
from passlib.context import CryptContext
import os
from datetime import datetime

# Initialize FastAPI app
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database connection pool
DATABASE_URL = os.getenv("DATABASE_URL")  # Vercel Postgres URL

async def init_db():
    try:
        # Connect to PostgreSQL
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            # Create tables
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS copied_text_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    text TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        logger.info("[INFO] Database initialized successfully")
        return pool
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize database: {e}")
        raise

# Global database pool
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await init_db()

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

# Pydantic models
class UserLogin(BaseModel):
    username: str
    password: str

# API endpoint to login
@app.post("/login")
async def login(user: UserLogin):
    logger.info(f"[INFO] Login attempt for user: {user.username}")
    try:
        async with pool.acquire() as conn:
            # Check if user exists
            result = await conn.fetchrow(
                "SELECT * FROM users WHERE username = $1", user.username
            )
            if result:
                # Verify password
                if pwd_context.verify(user.password, result["password"]):
                    logger.info(f"[INFO] User {user.username} logged in successfully")
                    # Log user activity
                    await conn.execute(
                        "INSERT INTO user_activity (user_id, action, timestamp) VALUES ($1, $2, $3)",
                        result["id"], "login", datetime.utcnow()
                    )
                    return {"status": "success", "message": "Login successful", "user_id": result["id"]}
                else:
                    logger.warning(f"[WARNING] Invalid password for user {user.username}")
                    raise HTTPException(status_code=401, detail="Invalid credentials")
            else:
                logger.warning(f"[WARNING] User {user.username} not found")
                raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred during login: {e}")
        raise HTTPException(status_code=500, detail="Failed to process login")

# API endpoint to fetch copied text history
@app.get("/fetch-copied-text/{user_id}")
async def fetch_copied_text(user_id: int):
    logger.info(f"[INFO] Fetching copied text history for user_id: {user_id}")
    try:
        async with pool.acquire() as conn:
            history_items = await conn.fetch(
                "SELECT text FROM copied_text_history WHERE user_id = $1 ORDER BY timestamp DESC",
                user_id
            )
            history_items = [item["text"] for item in history_items]
            logger.info(f"[INFO] Copied text history fetched for user_id {user_id}: {history_items}")
            return {"status": "success", "history": history_items}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while fetching copied text history: {e}")
        return {"status": "error", "message": "Failed to fetch copied text history"}

# Serve the index.html file
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    logger.info("[INFO] Serving index.html")
    return templates.TemplateResponse("index.html", {"request": request})