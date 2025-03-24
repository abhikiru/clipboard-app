import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")  # Replace with a secure key later

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Database connection (Neon)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

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

# Create tables
metadata.create_all(engine)

# Set up database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create default admin and user on startup
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        # Default admin
        if not db.execute(users.select().where(users.c.username == "admin1")).fetchone():
            db.execute(users.insert().values(username="admin1", password="adminpass1", role="admin"))
        # Default user
        if not db.execute(users.select().where(users.c.username == "user1")).fetchone():
            db.execute(users.insert().values(username="user1", password="userpass1", role="user"))
        db.commit()

        # Log all users to verify
        all_users = db.execute(users.select()).fetchall()
        print("Users in database on startup:")
        for user in all_users:
            print(f"ID: {user.id}, Username: {user.username}, Password: {user.password}, Role: {user.role}")
    finally:
        db.close()


# Pydantic model for history items
class HistoryItem(BaseModel):
    text: str


# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: str = None):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": error})


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
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid ID or password"})
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
async def user_login_page(request: Request, error: str = None):
    return templates.TemplateResponse("user_login.html", {"request": request, "error": error})


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
        return templates.TemplateResponse("user_login.html", {"request": request, "error": "Invalid ID or password"})
    finally:
        db.close()


@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    if request.session.get("user", {}).get("role") != "user":
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("user_dashboard.html",
                                      {"request": request, "username": request.session["user"]["username"]})


@app.post("/update-history/{username}")
async def update_history(username: str, item: HistoryItem):
    db = SessionLocal()
    try:
        db.execute(history.insert().values(username=username, text=item.text))
        db.commit()

        # Enforce max 10 history items
        items = db.execute(history.select().where(history.c.username == username)).fetchall()
        if len(items) > 10:
            items_to_delete = len(items) - 10
            db.execute(history.delete().where(history.c.username == username).where(history.c.id.in_(
                [item.id for item in sorted(items, key=lambda x: x.id)[:items_to_delete]]
            )))
            db.commit()
        return {"status": "success", "message": "History updated"}
    finally:
        db.close()


@app.get("/fetch-history/{username}")
async def fetch_history(username: str):
    db = SessionLocal()
    try:
        items = db.execute(
            history.select().where(history.c.username == username).order_by(history.c.id.desc())).fetchall()
        return {"status": "success", "history": [item.text for item in items]}
    finally:
        db.close()


@app.post("/delete-history/{username}")
async def delete_history(username: str, item: HistoryItem):
    db = SessionLocal()
    try:
        db.execute(history.delete().where(history.c.username == username).where(history.c.text == item.text))
        db.commit()
        return {"status": "success", "message": "History item deleted"}
    finally:
        db.close()


@app.post("/clear-history/{username}")
async def clear_history(username: str):
    db = SessionLocal()
    try:
        db.execute(history.delete().where(history.c.username == username))
        db.commit()
        return {"status": "success", "message": "History cleared"}
    finally:
        db.close()


@app.post("/update-copied-text/{username}")
async def update_copied_text(username: str, item: HistoryItem):
    db = SessionLocal()
    try:
        db.execute(copied_text_history.insert().values(username=username, text=item.text))
        db.commit()

        # Enforce max 10 copied text items
        items = db.execute(copied_text_history.select().where(copied_text_history.c.username == username)).fetchall()
        if len(items) > 10:
            items_to_delete = len(items) - 10
            db.execute(copied_text_history.delete().where(copied_text_history.c.username == username).where(
                copied_text_history.c.id.in_(
                    [item.id for item in sorted(items, key=lambda x: x.id)[:items_to_delete]]
                )))
            db.commit()
        return {"status": "success", "message": "Copied text updated"}
    finally:
        db.close()


@app.get("/fetch-copied-text/{username}")
async def fetch_copied_text(username: str):
    db = SessionLocal()
    try:
        items = db.execute(copied_text_history.select().where(copied_text_history.c.username == username).order_by(
            copied_text_history.c.id.desc())).fetchall()
        return {"status": "success", "history": [item.text for item in items]}
    finally:
        db.close()


@app.post("/delete-copied-text/{username}")
async def delete_copied_text(username: str, item: HistoryItem):
    db = SessionLocal()
    try:
        db.execute(copied_text_history.delete().where(copied_text_history.c.username == username).where(
            copied_text_history.c.text == item.text))
        db.commit()
        return {"status": "success", "message": "Copied text item deleted"}
    finally:
        db.close()


@app.post("/clear-copied-text/{username}")
async def clear_copied_text(username: str):
    db = SessionLocal()
    try:
        db.execute(copied_text_history.delete().where(copied_text_history.c.username == username))
        db.commit()
        return {"status": "success", "message": "Copied text history cleared"}
    finally:
        db.close()


# Helper function to get all users for admin dashboard
def get_all_users(db):
    return db.execute(users.select()).fetchall()