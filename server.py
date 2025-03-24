from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
import os
import time

# Database setup with Neon PostgreSQL
DATABASE_URL = (os.getenv("DATABASE_URL") or os.getenv("userurl")).replace("postgres://", "postgresql://")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    copied_texts = relationship("CopiedText", back_populates="user")

class CopiedText(Base):
    __tablename__ = "copied_texts"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="copied_texts")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

# FastAPI app setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper functions
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize default admin
def initialize_admin(db):
    admin = db.query(Admin).first()
    if not admin:
        hashed_password = get_password_hash("securepass2025")
        new_admin = Admin(username="superadmin", hashed_password=hashed_password)
        db.add(new_admin)
        db.commit()

# Middleware for session expiry
@app.middleware("http")
async def check_session_expiry(request: Request, call_next):
    protected_paths = ["/dashboard", "/admin/dashboard"]
    if any(request.url.path.startswith(path) for path in protected_paths):
        expiry = request.cookies.get("user_id_expiry") or request.cookies.get("admin_expiry")
        if not expiry or int(expiry) < int(time.time()):
            response = RedirectResponse(url="/", status_code=303)
            response.delete_cookie("user_id")
            response.delete_cookie("admin")
            return response
    return await call_next(request)

# Routes
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/user/login", response_class=HTMLResponse)
async def user_login_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/user/login")
async def user_login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid credentials"})
    response = RedirectResponse(url=f"/dashboard/{user.id}", status_code=303)
    response.set_cookie(key="user_id", value=user.id, httponly=True, secure=True, samesite="strict")
    response.set_cookie(key="user_id_expiry", value=int(time.time()) + 1800, httponly=True, secure=True, samesite="strict")
    return response

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_get(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    initialize_admin(db)
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not verify_password(password, admin.hashed_password):
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid credentials"})
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key="admin", value=admin.id, httponly=True, secure=True, samesite="strict")
    response.set_cookie(key="admin_expiry", value=int(time.time()) + 1800, httponly=True, secure=True, samesite="strict")
    return response

@app.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: int, page: int = 1, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    copied_texts = db.query(CopiedText).filter(CopiedText.user_id == user_id).offset((page - 1) * 10).limit(10).all()
    total_texts = db.query(CopiedText).filter(CopiedText.user_id == user_id).count()
    total_pages = (total_texts // 10) + 1
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "copied_texts": copied_texts,
        "page": page,
        "total_pages": total_pages
    })

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, search: str = "", page: int = 1, db: Session = Depends(get_db)):
    query = db.query(CopiedText)
    if search:
        query = query.join(User).filter(
            (User.username.ilike(f"%{search}%")) | (CopiedText.text.ilike(f"%{search}%"))
        )
    copied_texts = query.offset((page - 1) * 10).limit(10).all()
    total_texts = query.count()
    total_pages = (total_texts // 10) + 1
    users = db.query(User).all()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "users": users,
        "copied_texts": copied_texts,
        "search": search,
        "page": page,
        "total_pages": total_pages
    })

@app.post("/api/save_text")
async def save_text(request: Request, text: str = Form(...), db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id or len(text) > 1000 or not text.strip():
        raise HTTPException(status_code=400, detail="Invalid request")
    new_text = CopiedText(text=text, user_id=user_id)
    db.add(new_text)
    db.commit()
    return {"status": "success"}

@app.get("/user/logout")
async def user_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("user_id")
    response.delete_cookie("user_id_expiry")
    return response

@app.get("/admin/logout")
async def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin")
    response.delete_cookie("admin_expiry")
    return response

@app.post("/admin/add_user")
async def add_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if not (3 <= len(username) <= 20 and username.isalnum()) or not (8 <= len(password) <= 50 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        raise HTTPException(status_code=400, detail="Invalid input")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@app.post("/admin/delete_user/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@app.post("/admin/delete_text/{text_id}")
async def delete_text(text_id: int, db: Session = Depends(get_db)):
    text = db.query(CopiedText).filter(CopiedText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Text not found")
    db.delete(text)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)