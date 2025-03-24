import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")  # Replace with a secure key later

# Set up templates
templates = Jinja2Templates(directory="templates")

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define users table
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, nullable=False),
    Column("password", String(50), nullable=False),
    Column("role", String(10), nullable=False),
)

# Create the table if it doesn't exist
metadata.create_all(engine)

# Set up database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create default admin and user on startup if they don't exist
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        # Check and create default admin
        if not db.execute(users.select().where(users.c.username == "admin1")).fetchone():
            db.execute(users.insert().values(username="admin1", password="adminpass1", role="admin"))

        # Check and create default user
        if not db.execute(users.select().where(users.c.username == "user1")).fetchone():
            db.execute(users.insert().values(username="user1", password="userpass1", role="user"))

        db.commit()
    finally:
        db.close()


# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/admin/login")
async def admin_login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    db = SessionLocal()
    try:
        user = db.execute(users.select().where(users.c.username == username)).fetchone()
        if user and user.password == password and user.role == "admin":
            request.session["user"] = {"username": username, "role": "admin"}
            return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": get_all_users(db)})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    finally:
        db.close()


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if request.session.get("user", {}).get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    db = SessionLocal()
    try:
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": get_all_users(db)})
    finally:
        db.close()


@app.post("/admin/update_user")
async def update_user(request: Request):
    if request.session.get("user", {}).get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    form = await request.form()
    user_id = form.get("user_id")
    new_username = form.get("username")
    new_password = form.get("password")

    db = SessionLocal()
    try:
        db.execute(users.update().where(users.c.id == user_id).values(username=new_username, password=new_password))
        db.commit()
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": get_all_users(db),
                                                                   "message": "User updated successfully"})
    finally:
        db.close()


@app.get("/user/login", response_class=HTMLResponse)
async def user_login_page(request: Request):
    return templates.TemplateResponse("user_login.html", {"request": request})


@app.post("/user/login")
async def user_login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    db = SessionLocal()
    try:
        user = db.execute(users.select().where(users.c.username == username)).fetchone()
        if user and user.password == password and user.role == "user":
            request.session["user"] = {"username": username, "role": "user"}
            return templates.TemplateResponse("user_dashboard.html", {"request": request, "username": username})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    finally:
        db.close()


@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    if request.session.get("user", {}).get("role") != "user":
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("user_dashboard.html",
                                      {"request": request, "username": request.session["user"]["username"]})


# Helper function to get all users for admin dashboard
def get_all_users(db):
    return db.execute(users.select()).fetchall()