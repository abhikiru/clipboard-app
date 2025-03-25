import os
from fastapi import FastAPI, Request, HTTPException, Depends, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
import jwt
from fastapi.security import HTTPBearer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Session secret key from environment variable
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")

# Add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Database connection (Neon)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

print(f"Connecting to database with URL: {DATABASE_URL}")

engine = None
if os.getenv("VERCEL"):
    print("Running on Vercel, skipping database connection during build")
else:
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("Database connection successful")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        engine = None

# Define metadata for SQLAlchemy
metadata = MetaData()  # Properly define 'metadata' here

# Define tables
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, nullable=False),
    Column("password", String(50), nullable=False),
    Column("role", String(10), nullable=False),
)

history = Table(
    "history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), nullable=False),
    Column("text", String, nullable=False),
)

copied_text_history = Table(
    "copied_text_history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), nullable=False),
    Column("text", String, nullable=False),
)

# Create tables only if engine is available
if engine:
    try:
        metadata.create_all(engine)
        print("Tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        engine = None

# Set up database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


# Pydantic models
class User(BaseModel):
    username: str
    password: str


class TextData(BaseModel):
    text: str
    option: str


# Dependency to get database session
def get_db():
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="Database not available")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency for JWT authentication
security = HTTPBearer()


def verify_token(credentials=Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not engine:
        return HTMLResponse(
            content="<h1>Server Error</h1><p>Unable to connect to the database. Please try again later.</p>",
            status_code=500)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/user/login", response_class=HTMLResponse)
async def user_login_page(request: Request):
    return templates.TemplateResponse("user_login.html", {"request": request})


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/login")
async def login(user: User, request: Request, db=Depends(get_db)):
    query = users.select().where(users.c.username == user.username)
    result = db.execute(query).fetchone()

    if result and result.password == user.password:
        role = result.role
        token = jwt.encode({"username": user.username, "role": role}, JWT_SECRET_KEY, algorithm="HS256")
        request.session["token"] = token
        if role == "admin":
            return {"redirect": "/admin/dashboard"}
        return {"redirect": "/user/dashboard"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, payload=Depends(verify_token)):
    if payload.get("role") != "user":
        raise HTTPException(status_code=403, detail="Not authorized")
    username = payload.get("username")
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "username": username})


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    username = payload.get("username")
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "username": username})


@app.post("/update-history/{username}")
async def update_history(username: str, text_data: TextData, db=Depends(get_db)):
    if text_data.option in ["Add to History", "Both"]:
        query = history.insert().values(username=username, text=text_data.text)
        db.execute(query)
        db.commit()
    if text_data.option in ["Copy to Clipboard", "Both"]:
        query = copied_text_history.insert().values(username=username, text=text_data.text)
        db.execute(query)
        db.commit()
    return {"message": "Text processed successfully"}


@app.get("/get-history/{username}")
async def get_history(username: str, db=Depends(get_db)):
    query = history.select().where(history.c.username == username)
    result = db.execute(query).fetchall()
    return [{"id": row.id, "text": row.text} for row in result]


@app.get("/get-copied-text/{username}")
async def get_copied_text(username: str, db=Depends(get_db)):
    query = copied_text_history.select().where(copied_text_history.c.username == username)
    result = db.execute(query).fetchall()
    return [{"id": row.id, "text": row.text} for row in result]


# WebSocket for clipboard communication
connected_clients = {}


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str, token: str):
    await websocket.accept()
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        if payload.get("username") != username:
            await websocket.close(code=1008, reason="Invalid token")
            return
        connected_clients[username] = websocket
        while True:
            data = await websocket.receive_text()
            if username in connected_clients:
                await connected_clients[username].send_text(data)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if username in connected_clients:
            del connected_clients[username]
        await websocket.close()


# Debug endpoint to test database connection
@app.get("/debug/db")
async def debug_db(db=Depends(get_db)):
    try:
        result = db.execute("SELECT 1").fetchone()
        return {"status": "success", "result": result[0]}
    except Exception as e:
        return {"status": "error", "message": str(e)}