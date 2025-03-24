from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from passlib.context import CryptContext
import os

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
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)  # Store hashed password
    email = Column(String, unique=True)
    copied_texts = relationship("CopiedText", back_populates="user")


class CopiedText(Base):
    __tablename__ = "copied_text"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="copied_texts")


class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)  # Store hashed password


# Create tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Failed to create tables: {e}")
    raise e


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize default admin credentials if not present
def initialize_admin(db: Session):
    admin = db.query(Admin).first()
    if not admin:
        hashed_password = pwd_context.hash("securepass2025")
        default_admin = Admin(username="superadmin", password_hash=hashed_password)
        db.add(default_admin)
        db.commit()


# Routes
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/user/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/user/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            return templates.TemplateResponse("index.html",
                                              {"request": request, "error": "Invalid username or password"})

        print(f"User {username} logged in successfully, redirecting to /dashboard/{user.id}")
        response = RedirectResponse(url=f"/dashboard/{user.id}", status_code=303)
        response.set_cookie(key="user_id", value=str(user.id))
        return response
    except Exception as e:
        print(f"Login error: {e}")
        return templates.TemplateResponse("index.html", {"request": request, "error": "An error occurred during login"})


@app.get("/user/logout", response_class=RedirectResponse)
async def user_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("user_id")
    return response


@app.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: int, db: Session = Depends(get_db)):
    try:
        print(f"Accessing dashboard for user_id: {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"User with ID {user_id} not found, redirecting to /user/login")
            return RedirectResponse(url="/user/login", status_code=303)

        copied_texts = db.query(CopiedText).filter(CopiedText.user_id == user_id).all()
        print(f"Rendering dashboard for user: {user.username}")
        return templates.TemplateResponse("dashboard.html",
                                          {"request": request, "user": user, "copied_texts": copied_texts})
    except Exception as e:
        print(f"Dashboard error: {e}")
        return RedirectResponse(url="/user/login", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request, db: Session = Depends(get_db)):
    initialize_admin(db)  # Ensure default admin exists
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...),
                      db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not pwd_context.verify(password, admin.password_hash):
        return templates.TemplateResponse("admin_login.html",
                                          {"request": request, "error": "Invalid admin credentials"})

    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key="admin", value="true")
    return response


@app.get("/admin/logout", response_class=RedirectResponse)
async def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin")
    return response


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if request.cookies.get("admin") != "true":
        return RedirectResponse(url="/admin", status_code=303)

    users = db.query(User).all()
    copied_texts = db.query(CopiedText).join(User).all()
    admin = db.query(Admin).first()
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "users": users, "copied_texts": copied_texts,
                                       "admin": admin})


@app.post("/admin/add_user", response_class=HTMLResponse)
async def add_user(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...),
                   db: Session = Depends(get_db)):
    if request.cookies.get("admin") != "true":
        return RedirectResponse(url="/admin", status_code=303)

    try:
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
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "success": "User added successfully",
                                           "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})
    except Exception as e:
        print(f"Add user error: {e}")
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Failed to add user",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})


@app.post("/admin/update_user/{user_id}", response_class=HTMLResponse)
async def update_user(request: Request, user_id: int, username: str = Form(...), password: str = Form(...),
                      email: str = Form(...), db: Session = Depends(get_db)):
    if request.cookies.get("admin") != "true":
        return RedirectResponse(url="/admin", status_code=303)

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "User not found",
                                                                       "users": db.query(User).all(),
                                                                       "copied_texts": db.query(CopiedText).join(
                                                                           User).all(),
                                                                       "admin": db.query(Admin).first()})

        # Check if the new username is already taken by another user
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
    except Exception as e:
        print(f"Update user error: {e}")
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Failed to update user",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})


@app.post("/admin/delete_user/{user_id}", response_class=HTMLResponse)
async def delete_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    if request.cookies.get("admin") != "true":
        return RedirectResponse(url="/admin", status_code=303)

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "User not found",
                                                                       "users": db.query(User).all(),
                                                                       "copied_texts": db.query(CopiedText).join(
                                                                           User).all(),
                                                                       "admin": db.query(Admin).first()})

        db.delete(user)
        db.commit()
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "success": "User deleted successfully",
                                           "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})
    except Exception as e:
        print(f"Delete user error: {e}")
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Failed to delete user",
                                                                   "users": db.query(User).all(),
                                                                   "copied_texts": db.query(CopiedText).join(
                                                                       User).all(), "admin": db.query(Admin).first()})


@app.post("/admin/update_admin", response_class=HTMLResponse)
async def update_admin(request: Request, username: str = Form(...), password: str = Form(...),
                       db: Session = Depends(get_db)):
    if request.cookies.get("admin") != "true":
        return RedirectResponse(url="/admin", status_code=303)

    try:
        admin = db.query(Admin).first()
        if not admin:
            return templates.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Admin not found",
                                                                       "users": db.query(User).all(),
                                                                       "copied_texts": db.query(CopiedText).join(
                                                                           User).all(),
                                                                       "admin": db.query(Admin).first()})

        admin.username = username
        admin.password_hash = pwd_context.hash(password)
        db.commit()
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "success": "Admin credentials updated successfully",
                                           "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})
    except Exception as e:
        print(f"Update admin error: {e}")
        return templates.TemplateResponse("admin_dashboard.html",
                                          {"request": request, "error": "Failed to update admin credentials",
                                           "users": db.query(User).all(),
                                           "copied_texts": db.query(CopiedText).join(User).all(),
                                           "admin": db.query(Admin).first()})


@app.post("/api/save_text")
async def save_text(user_id: int, text: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_text = CopiedText(user_id=user_id, text=text)
        db.add(new_text)
        db.commit()
        return {"message": "Text saved successfully"}
    except Exception as e:
        print(f"Save text error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save text")