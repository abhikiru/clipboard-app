from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from passlib.context import CryptContext
import os
import re

# FastAPI app setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

try:
    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"Failed to connect to database: {e}")
    raise e

Base = declarative_base()


# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    copied_texts = relationship("CopiedText", back_populates="user")


class CopiedText(Base):
    __tablename__ = "copied_text"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="copied_texts")


class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)


# Create tables
Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize default admin credentials
def initialize_admin(db: Session):
    admin = db.query(Admin).first()
    if not admin:
        hashed_password = pwd_context.hash("securepass2025")
        default_admin = Admin(username="superadmin", password_hash=hashed_password)
        db.add(default_admin)
        db.commit()


# Input validation functions
def validate_username(username: str) -> bool:
    # Username: 3-20 characters, letters, numbers, underscores only
    return bool(re.match(r"^[a-zA-Z0-9_]{3,20}$", username))


def validate_password(password: str) -> bool:
    # Password: 8-50 characters, at least one letter and one number
    return bool(re.match(r"^(?=.*[a-zA-Z])(?=.*\d).{8,50}$", password))


def validate_email(email: str) -> bool:
    # Email: Basic email format validation
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))


# Session expiration settings
SESSION_DURATION = timedelta(minutes=30)  # Sessions expire after 30 minutes


def set_secure_cookie(response: RedirectResponse, key: str, value: str):
    # Set cookie with secure attributes and expiry timestamp
    expiry_timestamp = (datetime.utcnow() + SESSION_DURATION).isoformat()
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,  # Prevent JavaScript access
        secure=True,  # Only send over HTTPS
        samesite="Strict",  # Prevent CSRF
        expires=int(SESSION_DURATION.total_seconds())
    )
    response.set_cookie(
        key=f"{key}_expiry",
        value=expiry_timestamp,
        httponly=True,
        secure=True,
        samesite="Strict",
        expires=int(SESSION_DURATION.total_seconds())
    )


def check_session_expiry(request: Request, cookie_key: str) -> bool:
    # Check if session has expired
    expiry_timestamp = request.cookies.get(f"{cookie_key}_expiry")
    if not expiry_timestamp:
        return False
    try:
        expiry_time = datetime.fromisoformat(expiry_timestamp)
        return datetime.utcnow() < expiry_time
    except ValueError:
        return False


# Routes
# Landing Page
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


# User Login
@app.get("/user/login", response_class=HTMLResponse)
async def user_login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/user/login", response_class=HTMLResponse)
async def user_login(request: Request, username: str = Form(...), password: str = Form(...),
                     db: Session = Depends(get_db)):
    # Validate input
    if not validate_username(username):
        return templates.TemplateResponse("index.html", {"request": request,
                                                         "error": "Username must be 3-20 characters and contain only letters, numbers, or underscores"})
    if not validate_password(password):
        return templates.TemplateResponse("index.html", {"request": request,
                                                         "error": "Password must be 8-50 characters and contain at least one letter and one number"})

    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid username or password"})

    response = RedirectResponse(url=f"/dashboard/{user.id}", status_code=303)
    set_secure_cookie(response, "user_id", str(user.id))
    return response


@app.get("/user/logout", response_class=RedirectResponse)
async def user_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("user_id")
    response.delete_cookie("user_id_expiry")
    return response


# User Dashboard
@app.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def user_dashboard(request: Request, user_id: int, db: Session = Depends(get_db)):
    # Check session
    if not request.cookies.get("user_id") or request.cookies.get("user_id") != str(user_id) or not check_session_expiry(
            request, "user_id"):
        response = RedirectResponse(url="/user/login", status_code=303)
        response.delete_cookie("user_id")
        response.delete_cookie("user_id_expiry")
        return response

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/user/login", status_code=303)

    copied_texts = db.query(CopiedText).filter(CopiedText.user_id == user_id).all()
    return templates.TemplateResponse("dashboard.html",
                                      {"request": request, "user": user, "copied_texts": copied_texts})


# Admin Login
@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request, db: Session = Depends(get_db)):
    initialize_admin(db)
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...),
                      db: Session = Depends(get_db)):
    # Validate input
    if not validate_username(username):
        return templates.TemplateResponse("admin_login.html", {"request": request,
                                                               "error": "Username must be 3-20 characters and contain only letters, numbers, or underscores"})
    if not validate_password(password):
        return templates.TemplateResponse("admin_login.html", {"request": request,
                                                               "error": "Password must be 8-50 characters and contain at least one letter and one number"})

    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not pwd_context.verify(password, admin.password_hash):
        return templates.TemplateResponse("admin_login.html",
                                          {"request": request, "error": "Invalid admin credentials"})

    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    set_secure_cookie(response, "admin", "true")
    return response


@app.get("/admin/logout", response_class=RedirectResponse)
async def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin")
    response.delete_cookie("admin_expiry")
    return response


# Admin Dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.cookies.get("admin") or not check_session_expiry(request, "admin"):
        response = RedirectResponse(url="/admin", status_code=303)
        response.delete_cookie("admin")
        response.delete_cookie("admin_expiry")
        return response

    users = db.query(User).all()
    copied_texts = db.query(CopiedText).join(User).all()
    admin = db.query(Admin).first()
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "users": users, "copied_texts": copied_texts,
                                       "admin": admin})


# Admin: Add User
@app.post("/admin/add_user", response_class=HTMLResponse)
async def add_user(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...),
                   db: Session = Depends(get_db)):
    if not request.cookies.get("admin") or not check_session_expiry(request, "admin"):
        response = RedirectResponse(url="/admin", status_code=303)
        response.delete_cookie("admin")
        response.delete_cookie("admin_expiry")
        return response

    # Validate input
    if not validate_username(username):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request,
                                                                   "error": "Username must be 3-20 characters and contain only letters, numbers, or underscores",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})
    if not validate_password(password):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request,
                                                                   "error": "Password must be 8-50 characters and contain at least one letter and one number",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})
    if not validate_email(email):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Invalid email format",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "error": "Username already exists",
                                           "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})

    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, password_hash=hashed_password, email=email)
    db.add(new_user)
    db.commit()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "success": "User added successfully",
                                                               "users": db.query(User).all(),
                                                               "copied_texts": db.query(CopiedText).join(User).all(),
                                                               "admin": db.query(Admin).first()})


# Admin: Update User
@app.post("/admin/update_user/{user_id}", response_class=HTMLResponse)
async def update_user(request: Request, user_id: int, username: str = Form(...), password: str = Form(...),
                      email: str = Form(...), db: Session = Depends(get_db)):
    if not request.cookies.get("admin") or not check_session_expiry(request, "admin"):
        response = RedirectResponse(url="/admin", status_code=303)
        response.delete_cookie("admin")
        response.delete_cookie("admin_expiry")
        return response

    # Validate input
    if not validate_username(username):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request,
                                                                   "error": "Username must be 3-20 characters and contain only letters, numbers, or underscores",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})
    if not validate_password(password):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request,
                                                                   "error": "Password must be 8-50 characters and contain at least one letter and one number",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})
    if not validate_email(email):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Invalid email format",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "error": "User not found", "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})

    existing_user = db.query(User).filter(User.username == username, User.id != user_id).first()
    if existing_user:
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "error": "Username already exists",
                                           "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})

    user.username = username
    user.password_hash = pwd_context.hash(password)
    user.email = email
    db.commit()
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "success": "User updated successfully",
                                       "users": db.query(User).all(),
                                       "copied_texts": db.query(CopiedText).join(User).all(),
                                       "admin": db.query(Admin).first()})


# Admin: Delete User
@app.post("/admin/delete_user/{user_id}", response_class=HTMLResponse)
async def delete_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    if not request.cookies.get("admin") or not check_session_expiry(request, "admin"):
        response = RedirectResponse(url="/admin", status_code=303)
        response.delete_cookie("admin")
        response.delete_cookie("admin_expiry")
        return response

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "error": "User not found", "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})

    db.delete(user)
    db.commit()
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "success": "User deleted successfully",
                                       "users": db.query(User).all(),
                                       "copied_texts": db.query(CopiedText).join(User).all(),
                                       "admin": db.query(Admin).first()})


# Admin: Delete Copied Text
@app.post("/admin/delete_text/{text_id}", response_class=HTMLResponse)
async def delete_text(request: Request, text_id: int, db: Session = Depends(get_db)):
    if not request.cookies.get("admin") or not check_session_expiry(request, "admin"):
        response = RedirectResponse(url="/admin", status_code=303)
        response.delete_cookie("admin")
        response.delete_cookie("admin_expiry")
        return response

    text = db.query(CopiedText).filter(CopiedText.id == text_id).first()
    if not text:
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "error": "Text not found", "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})

    db.delete(text)
    db.commit()
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "success": "Text deleted successfully",
                                       "users": db.query(User).all(),
                                       "copied_texts": db.query(CopiedText).join(User).all(),
                                       "admin": db.query(Admin).first()})


# Admin: Update Admin Credentials
@app.post("/admin/update_admin", response_class=HTMLResponse)
async def update_admin(request: Request, username: str = Form(...), password: str = Form(...),
                       db: Session = Depends(get_db)):
    if not request.cookies.get("admin") or not check_session_expiry(request, "admin"):
        response = RedirectResponse(url="/admin", status_code=303)
        response.delete_cookie("admin")
        response.delete_cookie("admin_expiry")
        return response

    # Validate input
    if not validate_username(username):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request,
                                                                   "error": "Username must be 3-20 characters and contain only letters, numbers, or underscores",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})
    if not validate_password(password):
        return templates.TemplateResponse("admin_dashboard.html", {"request": request,
                                                                   "error": "Password must be 8-50 characters and contain at least one letter and one number",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})

    admin = db.query(Admin).first()
    if not admin:
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Admin not found",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})

    admin.username = username
    admin.password_hash = pwd_context.hash(password)
    db.commit()
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "success": "Admin credentials updated successfully",
                                       "users": db.query(User).all(),
                                       "copied_texts": db.query(CopiedText).join(User).all(),
                                       "admin": db.query(Admin).first()})


# API: Save Pasted Text
@app.post("/api/save_text")
async def save_text(user_id: int, text: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Basic validation for text (not empty, max length 1000 characters)
    if not text or len(text) > 1000:
        raise HTTPException(status_code=400, detail="Text must be non-empty and less than 1000 characters")

    new_text = CopiedText(user_id=user_id, text=text)
    db.add(new_text)
    db.commit()
    return {"message": "Text saved successfully"}