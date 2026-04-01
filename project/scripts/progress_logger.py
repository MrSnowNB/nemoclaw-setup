#!/usr/bin/env python3
"""
Progress Logger for Alice in Cyberland Execution Plan
Logs task executions to reports/daily/progress_<date>.yaml
"""

import os
import yaml
from datetime import datetime
from pathlib import Path

class ProgressLogger:
    def __init__(self, reports_dir="reports/daily"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def log_progress(self, task_id, status, duration_seconds=0, error_id=None, notes=""):
        """
        Log a task execution entry

        Args:
            task_id: Task ID (e.g., "T0.1")
            status: "started", "completed", "failed"
            duration_seconds: Task duration in seconds
            error_id: Error ID if failed (None otherwise)
            notes: Additional notes
        """
        timestamp = datetime.now().isoformat()
        date = datetime.now().strftime("%Y-%m-%d")

        filename = self.reports_dir / f"progress_{date}.yaml"

        entry = {
            "timestamp": timestamp,
            "task_id": task_id,
            "status": status,
            "duration_seconds": duration_seconds,
            "error_id": error_id,
            "notes": notes
        }

        # Read existing entries if file exists
        if filename.exists():
            try:
                with open(filename, 'r') as f:
                    data = yaml.safe_load(f) or []
            except Exception as e:
                print(f"Warning: Could not read existing log: {e}")
                data = []
        else:
            data = []

        # Append new entry
        data.append(entry)

        # Write back
        try:
            with open(filename, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            print(f"✅ Logged {status} for {task_id} to {filename}")
        except Exception as e:
            print(f"Error logging progress: {e}")

    def test_log(self):
        """Test the logging function"""
        self.log_progress("TEST_TASK", "started", 0, None, "Test logging function")
        self.log_progress("TEST_TASK", "completed", 10, None, "Test completed successfully")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Log progress for Alice in Cyberland project")
    parser.add_argument('--task_id', required=True, help='Task ID')
    parser.add_argument('--status', required=True, choices=['started', 'completed', 'failed'], help='Status')
    parser.add_argument('--duration', type=int, default=0, help='Duration seconds')
    parser.add_argument('--error_id', default=None, help='Error ID')
    parser.add_argument('--notes', default='', help='Notes')

    args = parser.parse_args()

    logger = ProgressLogger()
    logger.log_progress(args.task_id, args.status, args.duration, args.error_id, args.notes)
