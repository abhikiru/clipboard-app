from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta

# FastAPI app setup
app = FastAPI()

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")  # Replace with a secure key

# Database setup (replace with your Neon PostgreSQL URL)
DATABASE_URL = "postgresql://neondb_owner:npg_OhQR57ypVXH@ep-misty-leaf-a5xvgk2g-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy base
Base = declarative_base()

# Models
class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # Storing plain text password

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)  # Storing plain text password
    copied_texts = relationship("CopiedText", back_populates="user")

class CopiedText(Base):
    __tablename__ = "copied_texts"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="copied_texts")

# Create tables (if not already created)
Base.metadata.create_all(bind=engine)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Templates setup (assuming you're using Jinja2 for rendering HTML)
templates = Jinja2Templates(directory="templates")

# Middleware to check session expiry
class CheckSessionExpiryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the session has an admin or user
        if "admin" in request.session:
            last_activity = request.session.get("last_activity")
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                if datetime.now() - last_activity_time > timedelta(minutes=30):
                    del request.session["admin"]
                    return RedirectResponse(url="/admin", status_code=303)
            request.session["last_activity"] = datetime.now().isoformat()
        elif "user" in request.session:
            last_activity = request.session.get("last_activity")
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                if datetime.now() - last_activity_time > timedelta(minutes=30):
                    del request.session["user"]
                    return RedirectResponse(url="/", status_code=303)
            request.session["last_activity"] = datetime.now().isoformat()
        return await call_next(request)

app.add_middleware(CheckSessionExpiryMiddleware)

# Routes

# Homepage
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Admin login page (GET)
@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

# Admin login (POST)
@app.post("/admin/login")
async def admin_login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or admin.hashed_password != password:  # Direct comparison
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid username or password"})
    # Successful login
    request.session["admin"] = admin.id
    request.session["last_activity"] = datetime.now().isoformat()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

# Admin dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if "admin" not in request.session:
        return RedirectResponse(url="/admin", status_code=303)
    # Fetch some data for the dashboard (e.g., all users)
    users = db.query(User).all()
    return templates.TemplateResponse("user_login.html", {"request": request, "users": users})

# Admin logout
@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.pop("admin", None)
    request.session.pop("last_activity", None)
    return RedirectResponse(url="/admin", status_code=303)

# User login page (GET)
@app.get("/user/login", response_class=HTMLResponse)
async def user_login_page(request: Request):
    return templates.TemplateResponse("user_login.html", {"request": request})

# User login (POST)
@app.post("/user/login")
async def user_login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != password:  # Direct comparison
        return templates.TemplateResponse("user_login.html", {"request": request, "error": "Invalid username or password"})
    # Successful login
    request.session["user"] = user.id
    request.session["last_activity"] = datetime.now().isoformat()
    return RedirectResponse(url="/user/dashboard", status_code=303)

# User dashboard
@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, db: Session = Depends(get_db)):
    if "user" not in request.session:
        return RedirectResponse(url="/user/login", status_code=303)
    user_id = request.session["user"]
    user = db.query(User).filter(User.id == user_id).first()
    copied_texts = db.query(CopiedText).filter(CopiedText.user_id == user_id).all()
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "user": user, "copied_texts": copied_texts})

# User registration (optional, if you want to allow registration)
@app.post("/user/register")
async def register_user(username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(username=username, email=email, password_hash=password)  # Store as plain text
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/user/login", status_code=303)

# Example: Initialize admin (run this once to create an admin if needed)
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        admin = db.query(Admin).first()
        if not admin:
            new_admin = Admin(username="admin", hashed_password="adminpass")
            db.add(new_admin)
            db.commit()
    finally:
        db.close()