"""Task management endpoints"""

from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify
from pymongo.errors import DuplicateKeyError
import logging

from ..utils.auth import require_auth
from ..utils.database import get_db
from ..models.task import Task
from ..models.inspection import Inspection

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

# -----------------------------------------------------------------------------
# Get tasks for current user
# -----------------------------------------------------------------------------

@tasks_bp.route("/", methods=["GET"])
@require_auth
def get_user_tasks():
    """Get tasks assigned to the current user"""
    user = request.current_user
    user_id = user["user_id"]
    role = user["role"]
    
    db = get_db()
    tasks_coll = db.get_collection("tasks")
    
    # Build query strictly scoped to the current user's own board
    # All roles only see tasks assigned TO them to avoid cross-user mixing
    if role in ("inspector", "manager", "it"):
        query = {"assigned_to_id": ObjectId(user_id)}
    else:
        query = {"assigned_to_id": ObjectId(user_id)}
    
    users_coll = db.get_collection("users")
    cursor = tasks_coll.find(query).sort("created_at", -1)
    results = []
    for doc in cursor:
        # Enrich with role labels for assignee/assigner
        try:
            assignee = users_coll.find_one({"_id": doc.get("assigned_to_id")}) or {}
            assigner = users_coll.find_one({"_id": doc.get("assigned_by_id")}) or {}
            doc["assigned_to_role"] = assignee.get("role")
            doc["assigned_by_role"] = assigner.get("role")
        except Exception:
            pass
        results.append(Task.from_dict(doc).public_view())

    # For inspectors, backfill tasks from inspections if missing
    if role == "inspector":
        inspections_coll = db.get_collection("inspections")
        templates_coll = db.get_collection("templates")
        users_coll = db.get_collection("users")
        # Include all statuses we need for inspector view
        insp_cursor = inspections_coll.find({
            "inspector_id": ObjectId(user_id),
            "status": {"$in": ["assigned", "in_progress", "submitted", "completed"]}
        }).sort("created_at", -1)

        # Build a lookup of existing task inspection_ids to avoid duplicates
        existing_insp_ids = set(
            [doc.get("inspection_id") for doc in tasks_coll.find({
                "assigned_to_id": ObjectId(user_id),
                "inspection_id": {"$ne": None}
            }, {"inspection_id": 1})]
        )

        # Today's date boundary (UTC)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)

        for insp_doc in insp_cursor:
            insp = Inspection.from_dict(insp_doc)
            if insp._id in existing_insp_ids:
                continue
            # Resolve template title for nicer task names
            tpl_title = None
            try:
                tpl_doc = templates_coll.find_one({"_id": insp.template_id}, {"title": 1})
                if tpl_doc:
                    tpl_title = tpl_doc.get("title")
            except Exception:
                tpl_title = None
            # Create task document for missing inspection
            try:
                # Map inspection.status -> task.status with special rule: 'assigned' only for today
                mapped_status = None
                if insp.status == "assigned":
                    created = insp.created_at or insp.updated_at or datetime.utcnow()
                    if today_start <= created <= today_end:
                        mapped_status = "todo"  # Today's assigned inspection
                    else:
                        mapped_status = None  # skip older assigned
                elif insp.status == "in_progress":
                    mapped_status = "in_progress"  # currently working
                elif insp.status == "submitted":
                    mapped_status = "review"  # sent for review
                elif insp.status == "completed":
                    mapped_status = "completed"  # accepted by manager

                if mapped_status is None:
                    continue

                # Optional: resolve manager name for role line on frontend
                manager_name = ""
                try:
                    mgr = users_coll.find_one({"_id": insp.manager_id}) or {}
                    manager_name = f"{mgr.get('firstName','')} {mgr.get('lastName','')}".strip()
                except Exception:
                    manager_name = ""

                task = Task(
                    title=(tpl_title or "Inspection"),
                    description="Complete the assigned inspection",
                    priority="medium",
                    status=mapped_status,
                    is_completed=(mapped_status == "completed"),
                    inspection_id=insp._id,
                    template_title=tpl_title,
                    assigned_to_id=user_id,
                    assigned_by_id=insp.manager_id,
                    assigned_to_name="",
                    assigned_by_name=manager_name,
                    due_date=insp.scheduled_date,
                )
                ins_res = tasks_coll.insert_one(task.to_dict())
                task._id = ins_res.inserted_id
                results.append(task.public_view())
            except Exception as e:  # noqa: BLE001 – non-critical
                logger.error(f"Backfill task creation failed for inspection {insp._id}: {e}")

    # For managers, backfill tasks from templates assigned to them
    if role == "manager":
        templates_coll = db.get_collection("templates")
        # Map template.status -> task.status for Kanban
        status_map = {
            "submitted": "review",
            "manager_edit": "in_progress",
            "published": "todo"
        }
        tpl_cursor = templates_coll.find({
            "manager_id": ObjectId(user_id),
            "status": {"$in": ["submitted", "manager_edit", "published"]}
        }).sort("updated_at", -1)

        # Avoid duplicates by checking existing task template_ids
        existing_tpl_ids = set(
            [doc.get("template_id") for doc in tasks_coll.find({
                "assigned_to_id": ObjectId(user_id),
                "template_id": {"$ne": None}
            }, {"template_id": 1})]
        )

        for tpl_doc in tpl_cursor:
            tpl_id = tpl_doc.get("_id")
            if tpl_id in existing_tpl_ids:
                continue
            try:
                task = Task(
                    title=f"Template: {tpl_doc.get('title', 'Untitled')}",
                    description=f"from it – name: " or "",
                    priority="medium",
                    status=status_map.get(tpl_doc.get("status"), "todo"),
                    is_completed=False,
                    template_id=tpl_id,
                    template_title=tpl_doc.get("title"),
                    assigned_to_id=user_id,
                    assigned_by_id=tpl_doc.get("creator_id"),
                    assigned_to_name="",
                    assigned_by_name="",
                    due_date=None,
                )
                ins_res = tasks_coll.insert_one(task.to_dict())
                task._id = ins_res.inserted_id
                results.append(task.public_view())
            except Exception as e:  # noqa: BLE001 – non-critical
                logger.error(f"Backfill task creation failed for template {tpl_id}: {e}")
    
    return jsonify({"success": True, "data": results})

# -----------------------------------------------------------------------------
# Create new task
# -----------------------------------------------------------------------------

@tasks_bp.route("/", methods=["POST"])
@require_auth
def create_task():
    """Create a new task"""
    user = request.current_user
    payload = request.get_json() or {}
    
    # Validate required fields
    required_fields = ["title", "assigned_to_id"]
    if not all(field in payload for field in required_fields):
        return jsonify({
            "success": False, 
            "message": f"Missing required fields: {required_fields}"
        }), 400
    
    db = get_db()
    tasks_coll = db.get_collection("tasks")
    users_coll = db.get_collection("users")
    
    # Get assigned user details
    assigned_user = users_coll.find_one({"_id": ObjectId(payload["assigned_to_id"])})
    if not assigned_user:
        return jsonify({
            "success": False, 
            "message": "Assigned user not found"
        }), 404
    
    # Create task
    task = Task(
        title=payload["title"],
        description=payload.get("description", ""),
        priority=payload.get("priority", "medium"),
        status=payload.get("status", "todo"),
        assigned_to_id=payload["assigned_to_id"],
        assigned_by_id=user["user_id"],
        assigned_to_name=f"{assigned_user.get('firstName', '')} {assigned_user.get('lastName', '')}".strip(),
        assigned_by_name=f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
        due_date=datetime.fromisoformat(payload["due_date"]) if payload.get("due_date") else None,
    )
    
    try:
        result = tasks_coll.insert_one(task.to_dict())
        task._id = result.inserted_id
        
        return jsonify({
            "success": True, 
            "data": task.public_view(),
            "message": "Task created successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({
            "success": False, 
            "message": "Failed to create task"
        }), 500

# -----------------------------------------------------------------------------
# Update task status
# -----------------------------------------------------------------------------

@tasks_bp.route("/<task_id>/status", methods=["PUT"])
@require_auth
def update_task_status(task_id):
    """Update task status"""
    user = request.current_user
    payload = request.get_json() or {}
    
    if "status" not in payload:
        return jsonify({
            "success": False, 
            "message": "Status is required"
        }), 400
    
    db = get_db()
    tasks_coll = db.get_collection("tasks")
    
    # Find task
    task_doc = tasks_coll.find_one({"_id": ObjectId(task_id)})
    if not task_doc:
        return jsonify({
            "success": False, 
            "message": "Task not found"
        }), 404
    
    task = Task.from_dict(task_doc)
    
    # Check if user can update this task
    if user["role"] != "manager" and str(task.assigned_to_id) != user["user_id"]:
        return jsonify({
            "success": False, 
            "message": "You can only update your own tasks"
        }), 403
    
    try:
        # Update status
        task.update_status(payload["status"])
        
        # Save to database
        tasks_coll.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": task.to_dict(include_id=False)}
        )
        
        return jsonify({
            "success": True, 
            "data": task.public_view(),
            "message": "Task status updated successfully"
        })
        
    except ValueError as e:
        return jsonify({
            "success": False, 
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        return jsonify({
            "success": False, 
            "message": "Failed to update task status"
        }), 500

# -----------------------------------------------------------------------------
# Mark task as completed
# -----------------------------------------------------------------------------

@tasks_bp.route("/<task_id>/complete", methods=["PUT"])
@require_auth
def complete_task(task_id):
    """Mark task as completed"""
    user = request.current_user
    
    db = get_db()
    tasks_coll = db.get_collection("tasks")
    
    # Find task
    task_doc = tasks_coll.find_one({"_id": ObjectId(task_id)})
    if not task_doc:
        return jsonify({
            "success": False, 
            "message": "Task not found"
        }), 404
    
    task = Task.from_dict(task_doc)
    
    # Check if user can complete this task
    if user["role"] != "manager" and str(task.assigned_to_id) != user["user_id"]:
        return jsonify({
            "success": False, 
            "message": "You can only complete your own tasks"
        }), 403
    
    try:
        # Mark as completed
        task.mark_completed()
        
        # Save to database
        tasks_coll.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": task.to_dict(include_id=False)}
        )
        
        return jsonify({
            "success": True, 
            "data": task.public_view(),
            "message": "Task marked as completed"
        })
        
    except Exception as e:
        logger.error(f"Error completing task: {e}")
        return jsonify({
            "success": False, 
            "message": "Failed to complete task"
        }), 500

# -----------------------------------------------------------------------------
# Delete task
# -----------------------------------------------------------------------------

@tasks_bp.route("/<task_id>", methods=["DELETE"])
@require_auth
def delete_task(task_id):
    """Delete a task"""
    user = request.current_user
    
    # Only managers can delete tasks
    if user["role"] != "manager":
        return jsonify({
            "success": False, 
            "message": "Only managers can delete tasks"
        }), 403
    
    db = get_db()
    tasks_coll = db.get_collection("tasks")
    
    # Find and delete task
    result = tasks_coll.delete_one({"_id": ObjectId(task_id)})
    
    if result.deleted_count == 0:
        return jsonify({
            "success": False, 
            "message": "Task not found"
        }), 404
    
    return jsonify({
        "success": True, 
        "message": "Task deleted successfully"
    })

# -----------------------------------------------------------------------------
# Get task statistics
# -----------------------------------------------------------------------------

@tasks_bp.route("/stats", methods=["GET"])
@require_auth
def get_task_stats():
    """Get task statistics for current user"""
    user = request.current_user
    user_id = user["user_id"]
    role = user["role"]
    
    db = get_db()
    tasks_coll = db.get_collection("tasks")
    
    # Build query based on user role
    if role == "inspector":
        query = {"assigned_to_id": ObjectId(user_id)}
    elif role == "manager":
        # Managers see tasks they assigned OR tasks assigned to them
        query = {
            "$or": [
                {"assigned_by_id": ObjectId(user_id)},  # Tasks they assigned
                {"assigned_to_id": ObjectId(user_id)}   # Tasks assigned to them
            ]
        }
    else:
        # IT users see tasks they assigned OR tasks assigned to them
        query = {
            "$or": [
                {"assigned_by_id": ObjectId(user_id)},  # Tasks they assigned
                {"assigned_to_id": ObjectId(user_id)}   # Tasks assigned to them
            ]
        }
    
    # Get counts by status
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    stats = {
        "todo": 0,
        "in_progress": 0,
        "review": 0,
        "completed": 0,
        "total": 0
    }
    
    for result in tasks_coll.aggregate(pipeline):
        status = result["_id"]
        count = result["count"]
        stats[status] = count
        stats["total"] += count
    
    return jsonify({
        "success": True, 
        "data": stats
    })
