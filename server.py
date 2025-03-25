import os
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
import json

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow requests from the desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for testing; restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")  # Replace with a secure key later

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Database connection (Neon)
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+psycopg://")
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

history_table = Table(
    "history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, nullable=False),
    Column("history", String, nullable=True),  # JSON string
    Column("copied_text_history", String, nullable=True),  # JSON string
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

# WebSocket clients (support multiple connections per user)
websocket_connections = {}  # {username: [websocket1, websocket2, ...]}

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

# Pydantic model for history items
class HistoryItem(BaseModel):
    text: str

# WebSocket endpoint
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    if username not in websocket_connections:
        websocket_connections[username] = []
    websocket_connections[username].append(websocket)
    print(f"WebSocket connected for {username}. Total connections: {len(websocket_connections[username])}")
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast the data to all clients for this user
            if username in websocket_connections:
                for ws in websocket_connections[username]:
                    if ws != websocket:  # Don't send back to the sender
                        await ws.send_text(data)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for {username}")
        websocket_connections[username].remove(websocket)
        if not websocket_connections[username]:
            del websocket_connections[username]
        print(f"Remaining connections for {username}: {len(websocket_connections.get(username, []))}")

# Broadcast function to notify clients
async def broadcast_to_user(username: str, message: dict):
    if username in websocket_connections:
        print(f"Broadcasting to {len(websocket_connections[username])} clients for user {username}: {message}")
        for ws in websocket_connections[username]:
            await ws.send_json(message)

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
        if user:
            print(f"User found - Username: {user.username}, Password: {user.password}, Role: {user.role}")
            print(f"Comparing password: Input '{password}' vs Stored '{user.password}'")
            if user.password == password and user.role == "admin":
                print("Login successful, setting session")
                request.session["user"] = {"username": username, "role": "admin"}
                return templates.TemplateResponse("admin_dashboard.html",
                                                  {"request": request, "users": get_all_users(db)})
            else:
                print("Login failed: Password or role mismatch")
                return templates.TemplateResponse("admin_login.html",
                                                  {"request": request, "error": "Invalid ID or password"})
        else:
            print(f"Login failed: User '{username}' not found in database")
            return templates.TemplateResponse("admin_login.html",
                                              {"request": request, "error": "Invalid ID or password"})
    except Exception as e:
        print(f"Error during admin login: {e}")
        return templates.TemplateResponse("admin_login.html",
                                          {"request": request, "error": "Server error during login"})
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
        # Check if username already exists
        if db.execute(users.select().where(users.c.username == username)).fetchone():
            print(f"Add user failed: Username '{username}' already exists")
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": f"Username '{username}' already exists"
            })

        # Insert the new user
        db.execute(users.insert().values(username=username, password=password, role=role))
        db.commit()
        print("User added successfully")
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
        # Check if the new username is already taken by another user
        existing_user = db.execute(
            users.select().where(users.c.username == new_username).where(users.c.id != user_id)).fetchone()
        if existing_user:
            print(f"Update user failed: Username '{new_username}' already exists")
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": f"Username '{new_username}' already exists"
            })

        # Update the user
        update_values = {"username": new_username}
        if new_password:  # Only update password if a new one is provided
            update_values["password"] = new_password
        db.execute(users.update().where(users.c.id == user_id).values(**update_values))
        db.commit()
        print("User updated successfully")
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
        # Get the user to be deleted
        user_to_delete = db.execute(users.select().where(users.c.id == user_id)).fetchone()
        if not user_to_delete:
            print(f"Delete user failed: User ID '{user_id}' not found")
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": "User not found"
            })

        # Prevent the current admin from deleting themselves
        if user_to_delete.username == current_user:
            print(f"Delete user failed: Cannot delete the current admin '{current_user}'")
            return templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "users": get_all_users(db),
                "message": "Cannot delete your own account"
            })

        # Delete the user
        db.execute(users.delete().where(users.c.id == user_id))
        db.commit()
        print(f"User '{user_to_delete.username}' deleted successfully")
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

@app.get("/user/login", response_class=HTMLResponse)
async def user_login_page(request: Request, error: str = None):
    print("Serving user login page")
    return templates.TemplateResponse("user_login.html", {"request": request, "error": error})

@app.post("/user/login")
async def user_login(request: Request):
    form = await request.form()
    username = form.get("username").strip()
    password = form.get("password").strip()

    print(f"User login attempt - Username: {username}, Password: {password}")

    db = SessionLocal()
    try:
        user = db.execute(users.select().where(users.c.username == username)).fetchone()
        if user:
            print(f"User found - Username: {user.username}, Password: {user.password}, Role: {user.role}")
            print(f"Comparing password: Input '{password}' vs Stored '{user.password}'")
            if user.password == password and user.role == "user":
                print("Login successful, setting session")
                request.session["user"] = {"username": username, "role": "user"}
                return templates.TemplateResponse("user_dashboard.html", {"request": request, "username": username})
            else:
                print("Login failed: Password or role mismatch")
                return templates.TemplateResponse("user_login.html",
                                                  {"request": request, "error": "Invalid ID or password"})
        else:
            print(f"Login failed: User '{username}' not found in database")
            return templates.TemplateResponse("user_login.html",
                                              {"request": request, "error": "Invalid ID or password"})
    except Exception as e:
        print(f"Error during user login: {e}")
        return templates.TemplateResponse("user_login.html", {"request": request, "error": "Server error during login"})
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

# API endpoint to authenticate users (for the desktop app)
@app.post("/api/authenticate")
async def authenticate_user(request: Request):
    try:
        form = await request.form()
        print(f"Received form data: {dict(form)}")
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            print("Missing username or password in form data")
            return JSONResponse(content={"status": "error", "message": "Missing username or password"}, status_code=400)

        username = username.strip()
        password = password.strip()

        print(f"API authenticate attempt - Username: {username}, Password: {password}")

        db = SessionLocal()
        try:
            user = db.execute(users.select().where(users.c.username == username)).fetchone()
            if user and user.password == password:
                print(f"API authentication successful for user: {username}")
                return JSONResponse(content={"status": "success", "username": username, "role": user.role})
            else:
                print(f"API authentication failed for user: {username}")
                return JSONResponse(content={"status": "error", "message": "Invalid username or password"},
                                    status_code=401)
        except Exception as e:
            print(f"Error during API authentication: {e}")
            return JSONResponse(content={"status": "error", "message": "Server error"}, status_code=500)
        finally:
            db.close()
    except Exception as e:
        print(f"Error parsing form data: {e}")
        return JSONResponse(content={"status": "error", "message": "Invalid request format"}, status_code=400)

# API endpoint to fetch clipboard history for a user
@app.get("/api/history/{username}")
async def get_user_history(username: str):
    db = SessionLocal()
    try:
        user_history = db.execute(history_table.select().where(history_table.c.username == username)).fetchone()
        if user_history:
            history = json.loads(user_history.history) if user_history.history else []
            copied_text_history = json.loads(user_history.copied_text_history) if user_history.copied_text_history else []
            return JSONResponse(content={
                "status": "success",
                "history": history,
                "copied_text_history": copied_text_history
            })
        return JSONResponse(content={"status": "success", "history": [], "copied_text_history": []})
    except Exception as e:
        print(f"Error fetching history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error fetching history"}, status_code=500)
    finally:
        db.close()

# API endpoint to submit new clipboard data
@app.post("/api/submit/{username}")
async def submit_clipboard_data(username: str, item: HistoryItem):
    print(f"Received /api/submit/{username} request with text: {item.text}")
    db = SessionLocal()
    try:
        user_history = db.execute(history_table.select().where(history_table.c.username == username)).fetchone()
        if user_history:
            current_history = json.loads(user_history.history) if user_history.history else []
            current_history.insert(0, item.text)
            if len(current_history) > 50:  # Limit to 50 items
                current_history = current_history[:50]
            db.execute(
                history_table.update().where(history_table.c.username == username),
                {"history": json.dumps(current_history)}
            )
        else:
            db.execute(
                history_table.insert(),
                {"username": username, "history": json.dumps([item.text]), "copied_text_history": json.dumps([])}
            )
        db.commit()

        # Broadcast the update to all connected clients
        await broadcast_to_user(username, {"type": "history_update", "text": item.text})
        return JSONResponse(content={"status": "success", "message": "Clipboard data submitted"})
    except Exception as e:
        db.rollback()
        print(f"Error submitting clipboard data for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error submitting data"}, status_code=500)
    finally:
        db.close()

# API endpoint to submit new copied text (used by the desktop app)
@app.post("/api/submit_copied_text/{username}")
async def submit_copied_text(username: str, item: HistoryItem):
    print(f"Received /api/submit_copied_text/{username} request with text: {item.text}")
    db = SessionLocal()
    try:
        user_history = db.execute(history_table.select().where(history_table.c.username == username)).fetchone()
        if user_history:
            current_history = json.loads(user_history.copied_text_history) if user_history.copied_text_history else []
            current_history.insert(0, item.text)
            if len(current_history) > 50:  # Limit to 50 items
                current_history = current_history[:50]
            db.execute(
                history_table.update().where(history_table.c.username == username),
                {"copied_text_history": json.dumps(current_history)}
            )
        else:
            db.execute(
                history_table.insert(),
                {"username": username, "history": json.dumps([]), "copied_text_history": json.dumps([item.text])}
            )
        db.commit()

        # Broadcast the update to all connected clients
        await broadcast_to_user(username, {"type": "copied_text_update", "text": item.text})
        return JSONResponse(content={"status": "success", "message": "Copied text submitted"})
    except Exception as e:
        db.rollback()
        print(f"Error submitting copied text for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error submitting data"}, status_code=500)
    finally:
        db.close()

# API endpoint to delete a history item
@app.post("/api/delete_history/{username}")
async def delete_history(username: str, item: HistoryItem):
    db = SessionLocal()
    try:
        user_history = db.execute(history_table.select().where(history_table.c.username == username)).fetchone()
        if user_history:
            current_history = json.loads(user_history.history) if user_history.history else []
            if item.text in current_history:
                current_history.remove(item.text)
                db.execute(
                    history_table.update().where(history_table.c.username == username),
                    {"history": json.dumps(current_history)}
                )
                db.commit()
                await broadcast_to_user(username, {"type": "history_delete", "text": item.text})
        return JSONResponse(content={"status": "success", "message": "History item deleted"})
    except Exception as e:
        db.rollback()
        print(f"Error deleting history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error deleting history"}, status_code=500)
    finally:
        db.close()

# API endpoint to delete a copied text item
@app.post("/api/delete_copied_text/{username}")
async def delete_copied_text(username: str, item: HistoryItem):
    db = SessionLocal()
    try:
        user_history = db.execute(history_table.select().where(history_table.c.username == username)).fetchone()
        if user_history:
            current_history = json.loads(user_history.copied_text_history) if user_history.copied_text_history else []
            if item.text in current_history:
                current_history.remove(item.text)
                db.execute(
                    history_table.update().where(history_table.c.username == username),
                    {"copied_text_history": json.dumps(current_history)}
                )
                db.commit()
                await broadcast_to_user(username, {"type": "copied_text_delete", "text": item.text})
        return JSONResponse(content={"status": "success", "message": "Copied text item deleted"})
    except Exception as e:
        db.rollback()
        print(f"Error deleting copied text for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error deleting copied text"}, status_code=500)
    finally:
        db.close()

# API endpoint to clear history
@app.post("/api/clear_history/{username}")
async def clear_history(username: str):
    db = SessionLocal()
    try:
        db.execute(
            history_table.update().where(history_table.c.username == username),
            {"history": json.dumps([])}
        )
        db.commit()
        await broadcast_to_user(username, {"type": "history_clear"})
        return JSONResponse(content={"status": "success", "message": "History cleared"})
    except Exception as e:
        db.rollback()
        print(f"Error clearing history for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error clearing history"}, status_code=500)
    finally:
        db.close()

# API endpoint to clear copied text
@app.post("/api/clear_copied_text/{username}")
async def clear_copied_text(username: str):
    db = SessionLocal()
    try:
        db.execute(
            history_table.update().where(history_table.c.username == username),
            {"copied_text_history": json.dumps([])}
        )
        db.commit()
        await broadcast_to_user(username, {"type": "copied_text_clear"})
        return JSONResponse(content={"status": "success", "message": "Copied text history cleared"})
    except Exception as e:
        db.rollback()
        print(f"Error clearing copied text for {username}: {e}")
        return JSONResponse(content={"status": "error", "message": "Error clearing copied text"}, status_code=500)
    finally:
        db.close()

# Helper function to get all users for admin dashboard
def get_all_users(db):
    return db.execute(users.select()).fetchall()