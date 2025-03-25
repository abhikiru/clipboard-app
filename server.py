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

try:
    engine = create_engine(DATABASE_URL)
    print("Database connection successful")
except Exception as e:
    print(f"Failed to connect to database: {e}")
    raise

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
try:
    metadata.create_all(engine)
    print("Tables created successfully")
except Exception as e:
    print(f"Error creating tables: {e}")
    raise

# Set up database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# JWT settings
ALGORITHM = "HS256"

def create_token(username: str):
    return jwt.encode({"username": username}, JWT_SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload["username"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

security = HTTPBearer()

# Active WebSocket connections
active_connections = {}

# Pydantic model for history items
class HistoryItem(BaseModel):
    text: str

# Create default admin and user on startup
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        print("Starting database initialization")
        # Default admin
        if not db.execute(users.select().where(users.c.username == "admin1")).fetchone():
            db.execute(users.insert().values(username="admin1", password="adminpass1", role="admin"))
            print("Default admin created: admin1/adminpass1")
        else:
            print("Admin user 'admin1' already exists")

        # Default user
        if not db.execute(users.select().where(users.c.username == "user1")).fetchone():
            db.execute(users.insert().values(username="user1", password="userpass1", role="user"))
            print("Default user created: user1/userpass1")
        else:
            print("User 'user1' already exists")

        db.commit()

        # Log all users to verify
        all_users = db.execute(users.select()).fetchall()
        print("Users in database on startup:")
        for user in all_users:
            print(f"ID: {user.id}, Username: {user.username}, Password: {user.password}, Role: {user.role}")
    except Exception as e:
        print(f"Error during startup: {e}")
    finally:
        db.close()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: str = None):
    print("Serving admin login page")
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": error})

@app.post("/admin/login")
async def admin_login(request: Request):
    form = await request.form()
    username = form.get("username").strip()
    password = form.get("password").strip()
    print(f"Admin login attempt - Username: {username}, Password: {password}")
    db = SessionLocal()
    try:
        user = db.execute(users.select().where(users.c.username == username)).fetchone()
        if user and user.password == password and user.role == "admin":
            request.session["user"] = {"username": username, "role": "admin"}
            return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": get_all_users(db)})
        else:
            return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid ID or password"})
    finally:
        db.close()

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if request.session.get("user", {}).get("role") != "admin":
        print("Admin dashboard access denied: Not authorized")
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        print("Serving admin dashboard")
        return templates.TemplateResponse("admin_dashboard.html", {"request": request, "users": get_all_users(db)})
    finally:
        db.close()

@app.post("/admin/add_user")
async def add_user(request: Request):
    if request.session.get("user", {}).get("role") != "admin":
        print("Add user access denied: Not authorized")
        raise HTTPException(status_code=403, detail="Not authorized")
    form = await request.form()
    username = form.get("username").strip()
    password = form.get("password").strip()
    role = form.get("role").strip()
    print(f"Adding new user - Username: {username}, Password: {password}, Role: {role}")
    db = SessionLocal()
    try:
        if db.execute(users.select().where(users.c.username == username)).fetchone():
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": f"Username '{username}' already exists"
            })
        db.execute(users.insert().values(username=username, password=password, role=role))
        db.commit()
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "users": get_all_users(db),
            "message": f"User '{username}' added successfully"
        })
    except Exception as e:
        print(f"Error adding user: {e}")
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "users": get_all_users(db),
            "message": "Error adding user"
        })
    finally:
        db.close()

@app.post("/admin/update_user")
async def update_user(request: Request):
    if request.session.get("user", {}).get("role") != "admin":
        print("Update user access denied: Not authorized")
        raise HTTPException(status_code=403, detail="Not authorized")
    form = await request.form()
    user_id = form.get("user_id")
    new_username = form.get("username").strip()
    new_password = form.get("password").strip()
    print(f"Updating user - ID: {user_id}, New Username: {new_username}, New Password: {new_password}")
    db = SessionLocal()
    try:
        existing_user = db.execute(
            users.select().where(users.c.username == new_username).where(users.c.id != user_id)).fetchone()
        if existing_user:
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": f"Username '{new_username}' already exists"
            })
        update_values = {"username": new_username}
        if new_password:
            update_values["password"] = new_password
        db.execute(users.update().where(users.c.id == user_id).values(**update_values))
        db.commit()
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "users": get_all_users(db),
            "message": "User updated successfully"
        })
    except Exception as e:
        print(f"Error updating user: {e}")
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "users": get_all_users(db),
            "message": "Error updating user"
        })
    finally:
        db.close()

@app.post("/admin/delete_user")
async def delete_user(request: Request):
    if request.session.get("user", {}).get("role") != "admin":
        print("Delete user access denied: Not authorized")
        raise HTTPException(status_code=403, detail="Not authorized")
    form = await request.form()
    user_id = form.get("user_id")
    current_user = request.session.get("user", {}).get("username")
    print(f"Deleting user - ID: {user_id}")
    db = SessionLocal()
    try:
        user_to_delete = db.execute(users.select().where(users.c.id == user_id)).fetchone()
        if not user_to_delete:
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": "User not found"
            })
        if user_to_delete.username == current_user:
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": "Cannot delete your own account"
            })
        db.execute(users.delete().where(users.c.id == user_id))
        db.commit()
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "users": get_all_users(db),
            "message": f"User '{user_to_delete.username}' deleted successfully"
        })
    except Exception as e:
        print(f"Error deleting user: {e}")
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "users": get_all_users(db),
            "message": "Error deleting user"
        })
    finally:
        db.close()

@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    if request.session.get("user", {}).get("role") != "user":
        print("User dashboard access denied: Not authorized")
        raise HTTPException(status_code=403, detail="Not authorized")
    print("Serving user dashboard")
    return templates.TemplateResponse("user_dashboard.html",
                                      {"request": request, "username": request.session["user"]["username"]})

# API endpoint to fetch clipboard history for a user
@app.get("/api/history/{username}")
async def get_user_history(username: str, token: str = Depends(security)):
    verified_username = verify_token(token.credentials)
    if verified_username != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        history_items = db.execute(
            history.select().where(history.c.username == username).order_by(history.c.id.desc())).fetchall()
        copied_text_items = db.execute(
            copied_text_history.select().where(copied_text_history.c.username == username).order_by(
                copied_text_history.c.id.desc())).fetchall()
        return JSONResponse(content={
            "status": "success",
            "history": [item.text for item in history_items],
            "copied_text_history": [item.text for item in copied_text_items]
        })
    except Exception as e:
        print(f"Error fetching history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error fetching history"}, status_code=500)
    finally:
        db.close()

# API endpoint to submit new clipboard data
@app.post("/api/submit/{username}")
async def submit_clipboard_data(username: str, item: HistoryItem, token: str = Depends(security)):
    verified_username = verify_token(token.credentials)
    if verified_username != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        db.execute(history.insert().values(username=username, text=item.text))
        db.commit()
        items = db.execute(history.select().where(history.c.username == username)).fetchall()
        if len(items) > 10:
            items_to_delete = len(items) - 10
            db.execute(history.delete().where(history.c.username == username).where(history.c.id.in_(
                [item.id for item in sorted(items, key=lambda x: x.id)[:items_to_delete]]
            )))
            db.commit()
        return JSONResponse(content={"status": "success", "message": "Clipboard data submitted"})
    except Exception as e:
        print(f"Error submitting clipboard data for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error submitting data"}, status_code=500)
    finally:
        db.close()

# Update history (used by the website)
@app.post("/update-history/{username}")
async def update_history(username: str, item: HistoryItem, current_user: dict = Depends(get_current_user)):
    if current_user["username"] != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        db.execute(history.insert().values(username=username, text=item.text))
        db.commit()
        items = db.execute(history.select().where(history.c.username == username)).fetchall()
        if len(items) > 10:
            items_to_delete = len(items) - 10
            db.execute(history.delete().where(history.c.username == username).where(history.c.id.in_(
                [item.id for item in sorted(items, key=lambda x: x.id)[:items_to_delete]]
            )))
            db.commit()
        return JSONResponse(content={"status": "success", "message": "History updated"})
    except Exception as e:
        print(f"Error updating history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error updating history"}, status_code=500)
    finally:
        db.close()

# Fetch history (used by the website)
@app.get("/fetch-history/{username}")
async def fetch_history(username: str, current_user: dict = Depends(get_current_user)):
    if current_user["username"] != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        items = db.execute(
            history.select().where(history.c.username == username).order_by(history.c.id.desc())).fetchall()
        return JSONResponse(content={"status": "success", "history": [item.text for item in items]})
    except Exception as e:
        print(f"Error fetching history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error fetching history"}, status_code=500)
    finally:
        db.close()

# Delete history item
@app.post("/delete-history/{username}")
async def delete_history(username: str, item: HistoryItem, current_user: dict = Depends(get_current_user)):
    if current_user["username"] != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        db.execute(history.delete().where(history.c.username == username).where(history.c.text == item.text))
        db.commit()
        return JSONResponse(content={"status": "success", "message": "History item deleted"})
    except Exception as e:
        print(f"Error deleting history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error deleting history"}, status_code=500)
    finally:
        db.close()

# Clear history
@app.post("/clear-history/{username}")
async def clear_history(username: str, current_user: dict = Depends(get_current_user)):
    if current_user["username"] != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        db.execute(history.delete().where(history.c.username == username))
        db.commit()
        return JSONResponse(content={"status": "success", "message": "History cleared"})
    except Exception as e:
        print(f"Error clearing history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error clearing history"}, status_code=500)
    finally:
        db.close()

# Delete copied text item
@app.post("/delete-copied-text/{username}")
async def delete_copied_text(username: str, item: HistoryItem, current_user: dict = Depends(get_current_user)):
    if current_user["username"] != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        db.execute(copied_text_history.delete().where(copied_text_history.c.username == username).where(
            copied_text_history.c.text == item.text))
        db.commit()
        return JSONResponse(content={"status": "success", "message": "Copied text item deleted"})
    except Exception as e:
        print(f"Error deleting copied text for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error deleting copied text"}, status_code=500)
    finally:
        db.close()

# Clear copied text
@app.post("/clear-copied-text/{username}")
async def clear_copied_text(username: str, current_user: dict = Depends(get_current_user)):
    if current_user["username"] != username:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = SessionLocal()
    try:
        db.execute(copied_text_history.delete().where(copied_text_history.c.username == username))
        db.commit()
        return JSONResponse(content={"status": "success", "message": "Copied text history cleared"})
    except Exception as e:
        print(f"Error clearing copied text for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error clearing copied text"}, status_code=500)
    finally:
        db.close()

# Helper function to get all users for admin dashboard
def get_all_users(db):
    return db.execute(users.select()).fetchall()