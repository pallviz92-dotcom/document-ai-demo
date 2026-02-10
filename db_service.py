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


# ==========================================
# DASHBOARD ANALYTICS
# ==========================================

def get_dashboard_stats(user_id: str = None) -> dict:
    """Get aggregated dashboard statistics."""
    database = get_db()
    query = {"user_id": ObjectId(user_id)} if user_id else {}
    
    total_docs = database.extractions.count_documents(query)
    
    # Get today's count
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = {**query, "created_at": {"$gte": today}}
    docs_today = database.extractions.count_documents(today_query)
    
    # Average confidence from header fields
    pipeline = [
        {"$match": query},
        {"$unwind": {"path": "$header_fields", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": None, "avg_conf": {"$avg": "$header_fields.confidence"}}}
    ]
    conf_result = list(database.extractions.aggregate(pipeline))
    avg_confidence = round((conf_result[0]["avg_conf"] or 0) * 100, 1) if conf_result else 0
    
    # Document type distribution
    type_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$document_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    type_dist = list(database.extractions.aggregate(type_pipeline))
    
    return {
        "total_documents": total_docs,
        "docs_today": docs_today,
        "avg_confidence": avg_confidence,
        "document_types": [{"type": t["_id"] or "unknown", "count": t["count"]} for t in type_dist]
    }


def get_daily_extraction_counts(user_id: str = None, days: int = 30) -> list:
    """Get document counts per day for the last N days."""
    database = get_db()
    from datetime import timedelta
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = {"created_at": {"$gte": start_date}}
    if user_id:
        query["user_id"] = ObjectId(user_id)
    
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = list(database.extractions.aggregate(pipeline))
    return [{"date": r["_id"], "count": r["count"]} for r in results]


def get_confidence_trends(user_id: str = None, days: int = 30) -> list:
    """Get average confidence per day for the last N days."""
    database = get_db()
    from datetime import timedelta
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = {"created_at": {"$gte": start_date}}
    if user_id:
        query["user_id"] = ObjectId(user_id)
    
    pipeline = [
        {"$match": query},
        {"$unwind": {"path": "$header_fields", "preserveNullAndEmptyArrays": False}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "avg_confidence": {"$avg": "$header_fields.confidence"}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = list(database.extractions.aggregate(pipeline))
    return [{"date": r["_id"], "avg_confidence": round((r["avg_confidence"] or 0) * 100, 1)} for r in results]


def get_recent_extractions(user_id: str = None, limit: int = 50) -> list:
    """Get recent extractions for dashboard table."""
    database = get_db()
    query = {"user_id": ObjectId(user_id)} if user_id else {}
    
    extractions = database.extractions.find(query).sort("created_at", -1).limit(limit)
    
    results = []
    for e in extractions:
        # Compute average confidence
        fields = e.get("header_fields", [])
        confs = [f.get("confidence", 0) for f in fields if isinstance(f, dict) and "confidence" in f]
        avg_conf = round((sum(confs) / len(confs)) * 100, 1) if confs else 0
        
        results.append({
            "id": str(e["_id"]),
            "filename": e.get("filename"),
            "document_type": e.get("document_type"),
            "created_at": e.get("created_at").isoformat() if e.get("created_at") else None,
            "header_count": len(fields),
            "line_item_count": len(e.get("line_items", [])),
            "avg_confidence": avg_conf
        })
    
    return results


# ==========================================
# TEMPLATE LEARNING
# ==========================================

def save_template(user_id: str, vendor_name: str, document_type: str, field_mappings: dict) -> dict:
    """Save or update a vendor-specific field mapping template."""
    database = get_db()
    
    template = {
        "user_id": ObjectId(user_id),
        "vendor_name": vendor_name.strip(),
        "document_type": document_type,
        "field_mappings": field_mappings,
        "usage_count": 0,
        "updated_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc)
    }
    
    # Upsert: update if exists, insert if not
    result = database.templates.update_one(
        {"user_id": ObjectId(user_id), "vendor_name": vendor_name.strip()},
        {"$set": {
            "field_mappings": field_mappings,
            "document_type": document_type,
            "updated_at": datetime.now(timezone.utc)
        }, "$setOnInsert": {
            "created_at": datetime.now(timezone.utc),
            "usage_count": 0
        }},
        upsert=True
    )
    
    return {"success": True, "vendor": vendor_name}


def get_template(user_id: str, vendor_name: str) -> dict:
    """Get template for a specific vendor."""
    database = get_db()
    
    template = database.templates.find_one({
        "user_id": ObjectId(user_id),
        "vendor_name": vendor_name.strip()
    })
    
    if not template:
        return None
    
    # Increment usage count
    database.templates.update_one(
        {"_id": template["_id"]},
        {"$inc": {"usage_count": 1}}
    )
    
    return {
        "id": str(template["_id"]),
        "vendor_name": template["vendor_name"],
        "document_type": template.get("document_type"),
        "field_mappings": template.get("field_mappings", {}),
        "usage_count": template.get("usage_count", 0)
    }


def list_templates(user_id: str) -> list:
    """List all templates for a user."""
    database = get_db()
    
    templates = database.templates.find(
        {"user_id": ObjectId(user_id)}
    ).sort("updated_at", -1)
    
    return [
        {
            "id": str(t["_id"]),
            "vendor_name": t["vendor_name"],
            "document_type": t.get("document_type"),
            "field_count": len(t.get("field_mappings", {})),
            "usage_count": t.get("usage_count", 0),
            "updated_at": t.get("updated_at").isoformat() if t.get("updated_at") else None
        }
        for t in templates
    ]


def delete_template(template_id: str, user_id: str) -> bool:
    """Delete a template."""
    database = get_db()
    result = database.templates.delete_one({
        "_id": ObjectId(template_id),
        "user_id": ObjectId(user_id)
    })
    return result.deleted_count > 0

