from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import os

# FastAPI app setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

<<<<<<< HEAD
# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Fix postgres to postgresql in DATABASE_URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

try:
    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"Failed to connect to database: {e}")
    raise e

Base = declarative_base()
=======
# Database setup with error handling
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a

# Ensure the URL uses 'postgresql' instead of 'postgres'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

try:
    engine = create_engine(DATABASE_URL, echo=True)  # echo=True for debugging
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
    password = Column(String)
    email = Column(String, unique=True)
    copied_texts = relationship("CopiedText", back_populates="user")

class CopiedText(Base):
    __tablename__ = "copied_text"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="copied_texts")

<<<<<<< HEAD

# Create tables
=======
# Create tables in the database
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Failed to create tables: {e}")
    raise e
<<<<<<< HEAD

=======
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

<<<<<<< HEAD

# Owner credentials (you can change these)
OWNER_USERNAME = "admin"
OWNER_PASSWORD = "admin123"
=======
# Hardcoded owner credentials (for now)
OWNER_USERNAME = "owner"
OWNER_PASSWORD = "owner123"
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a

# Routes
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username, User.password == password).first()
        if not user:
<<<<<<< HEAD
            return templates.TemplateResponse("index.html",
                                              {"request": request, "error": "Invalid username or password"})

=======
            return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid username or password"})
        
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a
        response = RedirectResponse(url=f"/dashboard/{user.id}", status_code=303)
        response.set_cookie(key="user_id", value=str(user.id))
        return response
    except Exception as e:
        print(f"Login error: {e}")
        return templates.TemplateResponse("index.html", {"request": request, "error": "An error occurred during login"})
<<<<<<< HEAD

=======
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a

@app.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return RedirectResponse(url="/", status_code=303)
<<<<<<< HEAD

        copied_texts = db.query(CopiedText).filter(CopiedText.user_id == user_id).all()
        return templates.TemplateResponse("dashboard.html",
                                          {"request": request, "user": user, "copied_texts": copied_texts})
    except Exception as e:
        print(f"Dashboard error: {e}")
        return RedirectResponse(url="/", status_code=303)


=======
        
        copied_texts = db.query(CopiedText).filter(CopiedText.user_id == user_id).all()
        return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "copied_texts": copied_texts})
    except Exception as e:
        print(f"Dashboard error: {e}")
        return RedirectResponse(url="/", status_code=303)

>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a
@app.get("/owner", response_class=HTMLResponse)
async def owner_login_page(request: Request):
    return templates.TemplateResponse("owner_login.html", {"request": request})

@app.post("/owner/login", response_class=HTMLResponse)
async def owner_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username != OWNER_USERNAME or password != OWNER_PASSWORD:
        return templates.TemplateResponse("owner_login.html", {"request": request, "error": "Invalid owner credentials"})
    
    response = RedirectResponse(url="/owner/dashboard", status_code=303)
    response.set_cookie(key="owner", value="true")
    return response

@app.get("/owner/dashboard", response_class=HTMLResponse)
async def owner_dashboard(request: Request):
    if request.cookies.get("owner") != "true":
        return RedirectResponse(url="/owner", status_code=303)
    return templates.TemplateResponse("owner_dashboard.html", {"request": request})

@app.post("/owner/add_user", response_class=HTMLResponse)
async def add_user(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    if request.cookies.get("owner") != "true":
        return RedirectResponse(url="/owner", status_code=303)
    
    try:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return templates.TemplateResponse("owner_dashboard.html", {"request": request, "error": "Username already exists"})
        
        new_user = User(username=username, password=password, email=email)
        db.add(new_user)
        db.commit()
        return templates.TemplateResponse("owner_dashboard.html", {"request": request, "success": "User added successfully"})
    except Exception as e:
        print(f"Add user error: {e}")
        return templates.TemplateResponse("owner_dashboard.html", {"request": request, "error": "Failed to add user"})

<<<<<<< HEAD
    try:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return templates.TemplateResponse("owner_dashboard.html",
                                              {"request": request, "error": "Username already exists"})

        new_user = User(username=username, password=password, email=email)
        db.add(new_user)
        db.commit()
        return templates.TemplateResponse("owner_dashboard.html",
                                          {"request": request, "success": "User added successfully"})
    except Exception as e:
        print(f"Add user error: {e}")
        return templates.TemplateResponse("owner_dashboard.html", {"request": request, "error": "Failed to add user"})


=======
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a
@app.post("/api/save_text")
async def save_text(user_id: int, text: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
<<<<<<< HEAD

=======
        
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a
        new_text = CopiedText(user_id=user_id, text=text)
        db.add(new_text)
        db.commit()
        return {"message": "Text saved successfully"}
    except Exception as e:
        print(f"Save text error: {e}")
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail="Failed to save text")
=======
        raise HTTPException(status_code=500, detail="Failed to save text")
>>>>>>> eb91890203f5fd5d7ac59c022286406307862b1a
