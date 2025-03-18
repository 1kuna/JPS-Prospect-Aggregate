#!/usr/bin/env python

import os
import sys
import time

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from celery.result import AsyncResult
from src.celery_app import app

def check_task(task_id):
    """Check a task's status and result."""
    result = AsyncResult(task_id, app=app)
    print(f"Task state: {result.state}")
    
    if result.state == 'SUCCESS':
        print(f"Task result: {result.result}")
    elif result.state == 'FAILURE':
        print(f"Task error: {result.result}")
    else:
        print("Task is still running or in a different state")
    
    return result.state

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_task.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    
    # Check the task status
    state = check_task(task_id)
    
    # If the task is not done, check again after a delay
    if state not in ['SUCCESS', 'FAILURE']:
        print("Waiting 5 seconds to check again...")
        time.sleep(5)
        check_task(task_id) 