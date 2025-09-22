#!/usr/bin/env python3
"""
Database cleanup script for orphaned tasks.

This script helps clean up tasks that may have been created without proper user assignment
or that might be visible across users due to the previous bug.

Usage:
    python cleanup_orphaned_tasks.py [--dry-run]
    
Options:
    --dry-run    Show what would be deleted without actually deleting
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import argparse

# Add the parent directory to the path so we can import our config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config

def get_database():
    """Get database connection using the app config"""
    try:
        mongo_uri = os.environ.get('MONGODB_URI')
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable not set")
        
        client = MongoClient(mongo_uri)
        db = client['streamlineer']
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB")
        return db
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def find_orphaned_tasks(db):
    """Find tasks that don't have valid user assignments"""
    tasks_coll = db.get_collection("tasks")
    users_coll = db.get_collection("users")
    
    # Get all user IDs for validation
    user_ids = set(str(doc["_id"]) for doc in users_coll.find({}, {"_id": 1}))
    
    orphaned_tasks = []
    
    for task in tasks_coll.find({}):
        is_orphaned = False
        reasons = []
        
        # Check if assigned_to_id exists and is valid
        assigned_to = task.get("assigned_to_id")
        if not assigned_to:
            is_orphaned = True
            reasons.append("No assigned_to_id")
        elif str(assigned_to) not in user_ids:
            is_orphaned = True
            reasons.append("assigned_to_id points to non-existent user")
        
        # Check if assigned_by_id exists and is valid
        assigned_by = task.get("assigned_by_id")
        if not assigned_by:
            is_orphaned = True
            reasons.append("No assigned_by_id")
        elif str(assigned_by) not in user_ids:
            is_orphaned = True
            reasons.append("assigned_by_id points to non-existent user")
        
        if is_orphaned:
            orphaned_tasks.append({
                "task": task,
                "reasons": reasons
            })
    
    return orphaned_tasks

def cleanup_orphaned_tasks(db, dry_run=False):
    """Clean up orphaned tasks"""
    orphaned = find_orphaned_tasks(db)
    
    if not orphaned:
        print("✅ No orphaned tasks found!")
        return
    
    print(f"Found {len(orphaned)} orphaned task(s):")
    
    for item in orphaned:
        task = item["task"]
        reasons = item["reasons"]
        
        print(f"  - Task ID: {task['_id']}")
        print(f"    Title: {task.get('title', 'No title')}")
        print(f"    Reasons: {', '.join(reasons)}")
        print(f"    Created: {task.get('created_at', 'Unknown')}")
        print()
    
    if dry_run:
        print("🔍 DRY RUN: No tasks were deleted.")
        return
    
    # Ask for confirmation
    response = input(f"Delete {len(orphaned)} orphaned task(s)? [y/N]: ")
    if response.lower() != 'y':
        print("❌ Cleanup cancelled.")
        return
    
    tasks_coll = db.get_collection("tasks")
    task_ids = [item["task"]["_id"] for item in orphaned]
    
    result = tasks_coll.delete_many({"_id": {"$in": task_ids}})
    print(f"✅ Deleted {result.deleted_count} orphaned task(s).")

def main():
    parser = argparse.ArgumentParser(description="Clean up orphaned tasks in the database")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be deleted without actually deleting")
    
    args = parser.parse_args()
    
    print("🧹 Streamlineer Task Cleanup Script")
    print("=" * 40)
    
    db = get_database()
    cleanup_orphaned_tasks(db, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
