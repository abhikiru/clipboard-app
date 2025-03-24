from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
import json

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow desktop app requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for user sessions
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database setup (using Neon PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)

# Define History model
class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    text = Column(Text)

# Define CopiedText model
class CopiedText(Base):
    __tablename__ = "copied_text"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    text = Column(Text)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# User login page
@app.get("/user/login", response_class=HTMLResponse)
async def user_login_page(request: Request):
    return templates.TemplateResponse("user_login.html", {"request": request})

# User login handler
@app.post("/user/login", response_class=HTMLResponse)
async def user_login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.password == password, User.role == "user").first()
    if not user:
        return templates.TemplateResponse("user_login.html", {"request": request, "error": "Invalid ID or password"})
    request.session["username"] = username
    request.session["role"] = "user"
    return RedirectResponse(url="/user/dashboard", status_code=303)

# User dashboard
@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    username = request.session.get("username")
    role = request.session.get("role")
    if not username or role != "user":
        return RedirectResponse(url="/user/login", status_code=303)
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "username": username})

# Admin login page
@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

# Admin login handler
@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.password == password, User.role == "admin").first()
    if not user:
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid ID or password"})
    request.session["username"] = username
    request.session["role"] = "admin"
    return RedirectResponse(url="/admin/dashboard", status_code=303)

# Admin dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("username")
    role = request.session.get("role")
    if not username or role != "admin":
        return RedirectResponse(url="/admin", status_code=303)
    users = db.query(User).all()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users})

# Add new user
@app.post("/admin/add_user", response_class=HTMLResponse)
async def add_user(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form(...), db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/admin", status_code=303)
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        users = db.query(User).all()
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users, "message": "Username already exists"})
    new_user = User(username=username, password=password, role=role)
    db.add(new_user)
    db.commit()
    users = db.query(User).all()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users, "message": "User added successfully"})

# Update user
@app.post("/admin/update_user", response_class=HTMLResponse)
async def update_user(request: Request, user_id: int = Form(...), username: str = Form(...), password: str = Form(None), db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/admin", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        users = db.query(User).all()
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users, "message": "User not found"})
    user.username = username
    if password:
        user.password = password
    db.commit()
    users = db.query(User).all()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users, "message": "User updated successfully"})

# Delete user
@app.post("/admin/delete_user", response_class=HTMLResponse)
async def delete_user(request: Request, user_id: int = Form(...), db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/admin", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        users = db.query(User).all()
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users, "message": "User not found"})
    db.delete(user)
    db.commit()
    users = db.query(User).all()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": users, "message": "User deleted successfully"})

# API endpoint for desktop app authentication
@app.post("/api/authenticate")
async def authenticate(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.password == password).first()
    if not user:
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Invalid credentials"})
    return {"status": "success", "username": user.username, "role": user.role}

# Fetch history
@app.get("/fetch-history/{username}")
async def fetch_history(username: str, db: Session = Depends(get_db)):
    history = db.query(History).filter(History.username == username).all()
    return {"status": "success", "history": [item.text for item in history]}

# Update history
@app.post("/update-history/{username}")
async def update_history(username: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    text = data.get("text")
    new_history = History(username=username, text=text)
    db.add(new_history)
    db.commit()
    return {"status": "success"}

# Delete history item
@app.post("/delete-history/{username}")
async def delete_history(username: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    text = data.get("text")
    history_item = db.query(History).filter(History.username == username, History.text == text).first()
    if history_item:
        db.delete(history_item)
        db.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Item not found"}

# Clear history
@app.post("/clear-history/{username}")
async def clear_history(username: str, db: Session = Depends(get_db)):
    db.query(History).filter(History.username == username).delete()
    db.commit()
    return {"status": "success"}

# Fetch copied text
@app.get("/fetch-copied-text/{username}")
async def fetch_copied_text(username: str, db: Session = Depends(get_db)):
    copied_text = db.query(CopiedText).filter(CopiedText.username == username).all()
    return {"status": "success", "history": [item.text for item in copied_text]}

# Update copied text
@app.post("/update-copied-text/{username}")
async def update_copied_text(username: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    text = data.get("text")
    new_copied_text = CopiedText(username=username, text=text)
    db.add(new_copied_text)
    db.commit()
    return {"status": "success"}

# Delete copied text item
@app.post("/delete-copied-text/{username}")
async def delete_copied_text(username: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    text = data.get("text")
    copied_text_item = db.query(CopiedText).filter(CopiedText.username == username, CopiedText.text == text).first()
    if copied_text_item:
        db.delete(copied_text_item)
        db.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Item not found"}

# Clear copied text
@app.post("/clear-copied-text/{username}")
async def clear_copied_text(username: str, db: Session = Depends(get_db)):
    db.query(CopiedText).filter(CopiedText.username == username).delete()
    db.commit()
    return {"status": "success"}

# Initialize database with default users
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        # Check if users exist, if not, add default users
        if not db.query(User).filter(User.username == "user1").first():
            default_user = User(username="user1", password="userpass1", role="user")
            db.add(default_user)
        if not db.query(User).filter(User.username == "admin1").first():
            default_admin = User(username="admin1", password="adminpass1", role="admin")
            db.add(default_admin)
        db.commit()
    finally:
        db.close()