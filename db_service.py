"""MongoDB Database Service for Document AI."""

import os
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import bcrypt

# MongoDB connection
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/docai")
client = None
db = None


def get_db():
    """Get MongoDB database connection."""
    global client, db
    if db is None:
        client = MongoClient(MONGO_URI)
        db = client.get_database()
    return db


def init_db():
    """Initialize database collections and indexes."""
    database = get_db()
    
    # Create indexes
    database.users.create_index("email", unique=True)
    database.extractions.create_index("user_id")
    database.extractions.create_index("created_at")
    
    print("[INFO] MongoDB initialized successfully")
    return database


# ==========================================
# USER OPERATIONS
# ==========================================

def create_user(email: str, password: str, name: str = None) -> dict:
    """Create a new user."""
    database = get_db()
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    user = {
        "email": email.lower().strip(),
        "password_hash": password_hash,
        "name": name or email.split("@")[0],
        "created_at": datetime.now(timezone.utc),
        "extraction_count": 0
    }
    
    try:
        result = database.users.insert_one(user)
        user["_id"] = result.inserted_id
        return {"success": True, "user": sanitize_user(user)}
    except Exception as e:
        if "duplicate key" in str(e):
            return {"success": False, "error": "Email already registered"}
        return {"success": False, "error": str(e)}


def verify_user(email: str, password: str) -> dict:
    """Verify user credentials."""
    database = get_db()
    
    user = database.users.find_one({"email": email.lower().strip()})
    if not user:
        return {"success": False, "error": "Invalid email or password"}
    
    if bcrypt.checkpw(password.encode(), user["password_hash"]):
        return {"success": True, "user": sanitize_user(user)}
    
    return {"success": False, "error": "Invalid email or password"}


def get_user_by_id(user_id: str) -> dict:
    """Get user by ID."""
    database = get_db()
    user = database.users.find_one({"_id": ObjectId(user_id)})
    return sanitize_user(user) if user else None


def sanitize_user(user: dict) -> dict:
    """Remove sensitive data from user object."""
    if not user:
        return None
    return {
        "id": str(user.get("_id")),
        "email": user.get("email"),
        "name": user.get("name"),
        "created_at": user.get("created_at"),
        "extraction_count": user.get("extraction_count", 0)
    }


# ==========================================
# EXTRACTION OPERATIONS  
# ==========================================

def save_extraction(user_id: str, filename: str, document_type: str, result: dict) -> dict:
    """Save extraction result to database."""
    database = get_db()
    
    extraction = {
        "user_id": ObjectId(user_id),
        "filename": filename,
        "document_type": document_type,
        "created_at": datetime.now(timezone.utc),
        "status": result.get("status", "DONE"),
        "header_fields": result.get("extraction", {}).get("headerFields", []),
        "line_items": result.get("extraction", {}).get("lineItems", []),
        "raw_response": result
    }
    
    result_insert = database.extractions.insert_one(extraction)
    
    # Update user extraction count
    database.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"extraction_count": 1}}
    )
    
    return {
        "id": str(result_insert.inserted_id),
        "filename": filename,
        "created_at": extraction["created_at"].isoformat()
    }


def get_user_extractions(user_id: str, limit: int = 20) -> list:
    """Get user's extraction history."""
    database = get_db()
    
    extractions = database.extractions.find(
        {"user_id": ObjectId(user_id)}
    ).sort("created_at", -1).limit(limit)
    
    return [
        {
            "id": str(e["_id"]),
            "filename": e.get("filename"),
            "document_type": e.get("document_type"),
            "created_at": e.get("created_at").isoformat() if e.get("created_at") else None,
            "header_count": len(e.get("header_fields", [])),
            "line_item_count": len(e.get("line_items", []))
        }
        for e in extractions
    ]


def get_extraction_by_id(extraction_id: str, user_id: str) -> dict:
    """Get a specific extraction result."""
    database = get_db()
    
    extraction = database.extractions.find_one({
        "_id": ObjectId(extraction_id),
        "user_id": ObjectId(user_id)
    })
    
    if not extraction:
        return None
    
    return {
        "id": str(extraction["_id"]),
        "filename": extraction.get("filename"),
        "document_type": extraction.get("document_type"),
        "created_at": extraction.get("created_at").isoformat() if extraction.get("created_at") else None,
        "header_fields": extraction.get("header_fields", []),
        "line_items": extraction.get("line_items", []),
        "status": extraction.get("status")
    }
