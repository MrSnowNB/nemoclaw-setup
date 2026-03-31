"""
SELF-HEALING RECOVERY PROTOCOL (SHRP) v1.0
Checkpoint Manager - System State Snapshots & Deterministic Replay

Author: Cline AI Agent
Date: 2025-11-03
"""

import json
import hashlib
import pickle
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import os
import tempfile

from .shrp_logger import get_logger, EventType


class Checkpoint:
    """Represents a system state checkpoint"""

    def __init__(self, checkpoint_id: str, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        self.checkpoint_id = checkpoint_id
        self.state = state.copy() if isinstance(state, dict) else state
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the checkpoint state"""
        state_str = json.dumps(self.state, sort_keys=True, default=str)
        return hashlib.sha256(state_str.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary format"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.hash,
            "metadata": self.metadata,
            "state_keys": list(self.state.keys()) if isinstance(self.state, dict) else ["non_dict_state"]
        }


class SHRCheckpointManager:
    """
    SHRP v1.0 Checkpoint Manager
    Provides system state snapshots and deterministic replay capabilities
    """

    def __init__(self, checkpoint_dir: str = "outputs/checkpoints", max_checkpoints: int = 10):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_checkpoints = max_checkpoints
        self.logger = get_logger()

        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for checkpoint operations
        self._lock = threading.Lock()

        # In-memory checkpoint cache
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._checkpoint_order: List[str] = []  # For LRU management

        # Replay state
        self._replay_mode = False
        self._replay_sequence: List[str] = []
        self._current_replay_index = 0

    def create_checkpoint(
        self,
        state: Dict[str, Any],
        checkpoint_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_save: bool = True
    ) -> str:
        """
        Create a new checkpoint of the system state

        Args:
            state: The system state to checkpoint
            checkpoint_id: Optional custom checkpoint ID
            metadata: Additional metadata about the checkpoint
            auto_save: Whether to immediately save to disk

        Returns:
            checkpoint_id: The ID of the created checkpoint
        """

        if checkpoint_id is None:
            checkpoint_id = f"checkpoint_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{self._generate_short_hash()}"

        checkpoint = Checkpoint(checkpoint_id, state, metadata)

        with self._lock:
            # Store in memory
            self._checkpoints[checkpoint_id] = checkpoint
            self._checkpoint_order.append(checkpoint_id)

            # Manage LRU cache
            if len(self._checkpoint_order) > self.max_checkpoints:
                oldest_id = self._checkpoint_order.pop(0)
                del self._checkpoints[oldest_id]

            # Save to disk if requested
            if auto_save:
                self._save_checkpoint_to_disk(checkpoint)

        # Log checkpoint creation
        self.logger.log_checkpoint_create(checkpoint_id, state)

        return checkpoint_id

    def _generate_short_hash(self) -> str:
        """Generate a short random hash for checkpoint IDs"""
        return hashlib.md5(str(id(self)).encode()).hexdigest()[:8]

    def _save_checkpoint_to_disk(self, checkpoint: Checkpoint):
        """Save checkpoint to disk storage"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"

        try:
            # Save metadata and state separately for efficiency
            checkpoint_data = {
                "checkpoint_id": checkpoint.checkpoint_id,
                "timestamp": checkpoint.timestamp.isoformat(),
                "hash": checkpoint.hash,
                "metadata": checkpoint.metadata,
                "state": checkpoint.state
            }

            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.log_event(
                EventType.SYSTEM_ERROR,
                {
                    "component": "checkpoint_manager",
                    "operation": "save_checkpoint",
                    "error": str(e),
                    "checkpoint_id": checkpoint.checkpoint_id
                },
                severity="err"
            )
            raise

    def restore_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Restore system state from a checkpoint

        Args:
            checkpoint_id: The ID of the checkpoint to restore

        Returns:
            state: The restored system state

        Raises:
            KeyError: If checkpoint doesn't exist
            ValueError: If checkpoint integrity check fails
        """

        with self._lock:
            # Try memory first, then disk
            checkpoint = self._checkpoints.get(checkpoint_id)
            if checkpoint is None:
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
                if not checkpoint_file.exists():
                    raise KeyError(f"Checkpoint {checkpoint_id} does not exist")

                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)

                    # Reconstruct checkpoint object
                    checkpoint = Checkpoint(
                        checkpoint_data["checkpoint_id"],
                        checkpoint_data["state"],
                        checkpoint_data["metadata"]
                    )
                    checkpoint.timestamp = datetime.fromisoformat(checkpoint_data["timestamp"])
                    checkpoint.hash = checkpoint_data["hash"]

                    # Cache in memory
                    self._checkpoints[checkpoint_id] = checkpoint

                except Exception as e:
                    self.logger.log_event(
                        EventType.SYSTEM_ERROR,
                        {
                            "component": "checkpoint_manager",
                            "operation": "load_checkpoint",
                            "error": str(e),
                            "checkpoint_id": checkpoint_id
                        },
                        severity="err"
                    )
                    raise ValueError(f"Failed to load checkpoint {checkpoint_id}: {e}")

            # Verify integrity
            if checkpoint._calculate_hash() != checkpoint.hash:
                self.logger.log_event(
                    EventType.SYSTEM_ERROR,
                    {
                        "component": "checkpoint_manager",
                        "error": "checkpoint_integrity_check_failed",
                        "checkpoint_id": checkpoint_id,
                        "expected_hash": checkpoint.hash,
                        "actual_hash": checkpoint._calculate_hash()
                    },
                    severity="crit"
                )
                raise ValueError(f"Checkpoint {checkpoint_id} integrity check failed")

        # Log restoration
        self.logger.log_event(
            EventType.CHECKPOINT_RESTORE,
            {"checkpoint_id": checkpoint_id},
            tags=["checkpoint", "restore"]
        )

        return checkpoint.state

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints"""
        checkpoints = []

        # Get checkpoints from disk
        try:
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    checkpoints.append({
                        "checkpoint_id": checkpoint_data["checkpoint_id"],
                        "timestamp": checkpoint_data["timestamp"],
                        "metadata": checkpoint_data.get("metadata", {}),
                        "source": "disk"
                    })
                except:
                    continue
        except:
            pass

        # Add in-memory checkpoints that aren't on disk yet
        for checkpoint_id, checkpoint in self._checkpoints.items():
            if not any(cp["checkpoint_id"] == checkpoint_id for cp in checkpoints):
                checkpoints.append({
                    "checkpoint_id": checkpoint_id,
                    "timestamp": checkpoint.timestamp.isoformat(),
                    "metadata": checkpoint.metadata,
                    "source": "memory"
                })

        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)

        return checkpoints

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint

        Args:
            checkpoint_id: The ID of the checkpoint to delete

        Returns:
            success: True if deleted successfully, False otherwise
        """
        deleted_memory = False
        deleted_disk = False

        with self._lock:
            # Remove from memory
            if checkpoint_id in self._checkpoints:
                del self._checkpoints[checkpoint_id]
                deleted_memory = True

            if checkpoint_id in self._checkpoint_order:
                self._checkpoint_order.remove(checkpoint_id)

            # Remove from disk
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                try:
                    checkpoint_file.unlink()
                    deleted_disk = True
                except:
                    pass

        return deleted_memory or deleted_disk

    def start_replay(self, checkpoint_sequence: List[str]) -> bool:
        """
        Start deterministic replay mode with a sequence of checkpoints

        Args:
            checkpoint_sequence: Ordered list of checkpoint IDs to replay

        Returns:
            success: True if replay mode started successfully
        """
        # Verify all checkpoints exist
        available_checkpoints = self.list_checkpoints()
        available_ids = {cp["checkpoint_id"] for cp in available_checkpoints}

        missing_checkpoints = set(checkpoint_sequence) - available_ids
        if missing_checkpoints:
            self.logger.log_event(
                EventType.SYSTEM_ERROR,
                {
                    "component": "checkpoint_manager",
                    "error": "missing_checkpoints_for_replay",
                    "missing": list(missing_checkpoints),
                    "available": list(available_ids)
                },
                severity="err"
            )
            return False

        with self._lock:
            self._replay_mode = True
            self._replay_sequence = checkpoint_sequence.copy()
            self._current_replay_index = 0

        self.logger.log_event(
            EventType.CHECKPOINT_VERIFY,
            {
                "operation": "replay_started",
                "sequence_length": len(checkpoint_sequence),
                "checkpoints": checkpoint_sequence
            },
            tags=["replay", "start"]
        )

        return True

    def get_next_replay_state(self) -> Optional[Dict[str, Any]]:
        """
        Get the next state in the replay sequence

        Returns:
            state: Next checkpoint state, or None if replay finished
        """
        if not self._replay_mode or self._current_replay_index >= len(self._replay_sequence):
            return None

        checkpoint_id = self._replay_sequence[self._current_replay_index]
        state = self.restore_checkpoint(checkpoint_id)
        self._current_replay_index += 1

        return state

    def stop_replay(self):
        """Stop replay mode"""
        self._replay_mode = False
        self._replay_sequence = []
        self._current_replay_index = 0

        self.logger.log_event(
            EventType.CHECKPOINT_VERIFY,
            {"operation": "replay_stopped"},
            tags=["replay", "stop"]
        )

    @property
    def replay_mode(self) -> bool:
        """Check if replay mode is active"""
        return self._replay_mode

    @property
    def replay_progress(self) -> Dict[str, Any]:
        """Get current replay progress"""
        return {
            "active": self._replay_mode,
            "current_index": self._current_replay_index,
            "total_checkpoints": len(self._replay_sequence),
            "current_checkpoint": self._replay_sequence[self._current_replay_index] if self._replay_mode and self._current_replay_index < len(self._replay_sequence) else None,
            "completed": self._current_replay_index >= len(self._replay_sequence) if self._replay_mode else False
        }

    def clear_old_checkpoints(self, keep_recent: Optional[int] = None) -> int:
        """
        Clear old checkpoints, keeping only the most recent ones

        Args:
            keep_recent: Number of recent checkpoints to keep (default: max_checkpoints)

        Returns:
            deleted_count: Number of checkpoints deleted
        """
        if keep_recent is None:
            keep_recent = self.max_checkpoints

        checkpoints = self.list_checkpoints()
        if len(checkpoints) <= keep_recent:
            return 0

        # Sort by timestamp and keep only recent ones
        checkpoints_to_delete = checkpoints[keep_recent:]

        deleted_count = 0
        for cp in checkpoints_to_delete:
            if self.delete_checkpoint(cp["checkpoint_id"]):
                deleted_count += 1

        if deleted_count > 0:
            self.logger.log_event(
                EventType.SYSTEM_INFO,
                {
                    "component": "checkpoint_manager",
                    "operation": "cleared_old_checkpoints",
                    "deleted_count": deleted_count,
                    "kept_recent": keep_recent
                }
            )

        return deleted_count


# Global checkpoint manager instance
checkpoint_manager = SHRCheckpointManager()


def get_checkpoint_manager() -> SHRCheckpointManager:
    """Get the global SHRP checkpoint manager instance"""
    return checkpoint_manager
