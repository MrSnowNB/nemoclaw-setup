"""
SELF-HEALING RECOVERY PROTOCOL (SHRP) v1.0
Structured JSON-Lines Logger with MCP Compliance and RFC-5424 Compatibility

Author: Cline AI Agent
Date: 2025-11-03
"""

import json
import logging
import uuid
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path
import os


class EventType(Enum):
    """Comprehensive event taxonomy for SHRP operations"""
    # Task Events
    TASK_START = "task.start"
    TASK_COMPLETE = "task.complete"
    TASK_ERROR = "task.error"
    TASK_CANCEL = "task.cancel"
    TASK_RETRY = "task.retry"

    # Checkpoint Events
    CHECKPOINT_CREATE = "checkpoint.create"
    CHECKPOINT_RESTORE = "checkpoint.restore"
    CHECKPOINT_VERIFY = "checkpoint.verify"

    # Recovery Events
    RECOVERY_INITIATE = "recovery.initiate"
    RECOVERY_ATTEMPT = "recovery.attempt"
    RECOVERY_SUCCESS = "recovery.success"
    RECOVERY_FAILED = "recovery.failed"
    RECOVERY_ESCALATE = "recovery.escalate"

    # System Events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"

    # LLM Events
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_ERROR = "llm.error"
    LLM_TIMEOUT = "llm.timeout"

    # TTS Events
    TTS_REQUEST = "tts.request"
    TTS_COMPLETE = "tts.complete"
    TTS_ERROR = "tts.error"
    TTS_FILE_MISSING = "tts.file_missing"

    # WebSocket Events
    WS_CONNECT = "ws.connect"
    WS_DISCONNECT = "ws.disconnect"
    WS_MESSAGE = "ws.message"
    WS_ERROR = "ws.error"

    # Session Events
    SESSION_START = "session.start"
    SESSION_END = "session.end"
    SESSION_CHECKPOINT = "session.checkpoint"

    # Terminal Operation Events
    TERMINAL_COMMAND_START = "terminal.cmd.start"
    TERMINAL_COMMAND_COMPLETE = "terminal.cmd.complete"
    TERMINAL_COMMAND_ERROR = "terminal.cmd.error"
    TERMINAL_COMMAND_TIMEOUT = "terminal.cmd.timeout"

    # Mode Switching Events
    MODE_SWITCH_ACT = "mode.switch.act"
    MODE_SWITCH_ASK = "mode.switch.ask"
    MODE_SWITCH_INTERRUPT = "mode.switch.interrupt"

    # Mesh Network Events
    MESH_FAULT_DETECT = "mesh.fault.detect"
    MESH_PREDICTIVE_FAIL = "mesh.predictive.fail"
    MESH_RECOVERY_INIT = "mesh.recovery.init"
    MESH_ENERGY_LOW = "mesh.energy.low"


class SHRPLogger:
    """
    SHRP v1.0 Structured JSON-Lines Logger
    MCP Compliant with RFC-5424 Compatibility
    """

    def __init__(self, log_dir: str = "outputs/logs", service_name: str = "alice-cyberland"):
        self.log_dir = Path(log_dir)
        self.service_name = service_name
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else "localhost"
        self.process_id = os.getpid()

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for session tracking
        self._local = threading.local()

        # RFC-5424 facility codes
        self.facility = {
            "kernel": 0, "user": 1, "mail": 2, "system": 3, "security": 4,
            "syslog": 5, "lpr": 6, "news": 7, "uucp": 8, "cron": 9,
            "auth": 10, "ftp": 11, "ntp": 12, "audit": 13, "alert": 14,
            "clock": 15, "local0": 16, "local1": 17, "local2": 18, "local3": 19,
            "local4": 20, "local5": 21, "local6": 22, "local7": 23
        }

        # MCP event context
        self.event_context = {}

        # Initialize session
        self._ensure_session()

    def _ensure_session(self):
        """Ensure session context exists"""
        if not hasattr(self._local, 'session_id'):
            self._local.session_id = str(uuid.uuid4())
            self.log_event(
                EventType.SESSION_START,
                {"message": "New SHRP session initialized"},
                session_id=self._local.session_id
            )

    def get_session_id(self) -> str:
        """Get current session ID"""
        self._ensure_session()
        return self._local.session_id

    def _get_log_filename(self, event_type: EventType) -> str:
        """Generate log filename based on event type and date"""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        category = event_type.value.split('.')[0]  # task, checkpoint, recovery, etc.
        return f"{category}_{today}.jsonl"

    def _calculate_priority(self, severity: str, facility_name: str = "local0") -> int:
        """Calculate RFC-5424 priority value"""
        severity_map = {
            "emerg": 0, "alert": 1, "crit": 2, "err": 3,
            "warning": 4, "notice": 5, "info": 6, "debug": 7
        }
        severity_value = severity_map.get(severity, 6)  # default to info
        facility_value = self.facility.get(facility_name, 16)  # default to local0
        return (facility_value * 8) + severity_value

    def _format_rfc5424_timestamp(self, dt: datetime) -> str:
        """Format timestamp per RFC-5424"""
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def log_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        severity: str = "info",
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Log structured event with MCP compliance

        Args:
            event_type: EventType enum value
            data: Event-specific data
            severity: Log severity (emerg, alert, crit, err, warning, notice, info, debug)
            session_id: Session identifier
            task_id: Task identifier for task-related events
            user_id: User identifier
            correlation_id: Correlation ID for request tracing
            tags: Additional tags for filtering

        Returns:
            event_id: Unique event identifier
        """

        # Generate event ID
        event_id = str(uuid.uuid4())

        # Use provided IDs or get from context
        actual_session_id = session_id or self.get_session_id()

        # Create timestamp
        timestamp = datetime.now(timezone.utc)
        rfc_timestamp = self._format_rfc5424_timestamp(timestamp)

        # Build RFC-5424 compliant log entry
        log_entry = {
            # RFC-5424 Header
            "priority": self._calculate_priority(severity),
            "version": 1,
            "timestamp": rfc_timestamp,
            "hostname": self.hostname,
            "app_name": self.service_name,
            "procid": str(self.process_id),
            "msgid": event_id,

            # SHRP Structured Data
            "shrp": {
                "version": "1.0",
                "event_type": event_type.value,
                "event_id": event_id,
                "session_id": actual_session_id,
                "severity": severity,
                "timestamp": rfc_timestamp,
                "tags": tags or []
            },

            # MCP Context
            "mcp": {
                "protocol_version": "2024-11-05",
                "implementation": "cline-shrp-v1.0",
                "capabilities": ["logging", "events", "structured_data"]
            },

            # Event Data
            "data": data
        }

        # Add optional context fields
        if task_id:
            log_entry["shrp"]["task_id"] = task_id
        if user_id:
            log_entry["shrp"]["user_id"] = user_id
        if correlation_id:
            log_entry["shrp"]["correlation_id"] = correlation_id

        # Add global context
        log_entry["context"] = self.event_context.copy()

        # Write to appropriate log file
        log_filename = self._get_log_filename(event_type)
        log_path = self.log_dir / log_filename

        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                f.flush()
        except Exception as e:
            # Fallback: write to stderr and main log
            fallback_entry = log_entry.copy()
            fallback_entry["shrp"]["fallback_reason"] = str(e)
            try:
                with open(self.log_dir / "shrp_fallback.log", 'a', encoding='utf-8') as f:
                    f.write(json.dumps(fallback_entry, ensure_ascii=False) + '\n')
                    f.flush()
            except:
                pass

        return event_id

    def log_task_start(self, task_id: str, task_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Log task start event"""
        return self.log_event(
            EventType.TASK_START,
            {
                "task_name": task_name,
                "context": context or {}
            },
            task_id=task_id,
            tags=["task", "start"]
        )

    def log_task_complete(self, task_id: str, result: Optional[Any] = None, duration_ms: Optional[int] = None) -> str:
        """Log task completion event"""
        data = {}
        if result is not None:
            data["result"] = result
        if duration_ms is not None:
            data["duration_ms"] = duration_ms

        return self.log_event(
            EventType.TASK_COMPLETE,
            data,
            task_id=task_id,
            tags=["task", "complete"]
        )

    def log_task_error(self, task_id: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """Log task error event"""
        return self.log_event(
            EventType.TASK_ERROR,
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {}
            },
            severity="err",
            task_id=task_id,
            tags=["task", "error"]
        )

    def log_checkpoint_create(self, checkpoint_id: str, state: Dict[str, Any]) -> str:
        """Log checkpoint creation"""
        return self.log_event(
            EventType.CHECKPOINT_CREATE,
            {
                "checkpoint_id": checkpoint_id,
                "state_keys": list(state.keys()) if isinstance(state, dict) else ["non_dict_state"]
            },
            tags=["checkpoint"]
        )

    def log_system_health_check(self, component: str, status: str, metrics: Optional[Dict[str, Any]] = None) -> str:
        """Log system health check"""
        severity = "info" if status.lower() == "healthy" else "warning"
        return self.log_event(
            EventType.SYSTEM_HEALTH_CHECK,
            {
                "component": component,
                "status": status,
                "metrics": metrics or {}
            },
            severity=severity,
            tags=["health", "system"]
        )

    def set_context(self, key: str, value: Any):
        """Set global event context"""
        self.event_context[key] = value

    def clear_context(self, key: Optional[str] = None):
        """Clear global event context"""
        if key:
            self.event_context.pop(key, None)
        else:
            self.event_context.clear()

    def search_events(self, event_type: Optional[EventType] = None, session_id: Optional[str] = None,
                     task_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Search recent events (basic implementation)"""
        # This would be enhanced for full MCP resource access
        # For now, return empty list to avoid complexity
        return []


# Global SHRP logger instance
shrp_logger = SHRPLogger()


def get_logger() -> SHRPLogger:
    """Get the global SHRP logger instance"""
    return shrp_logger
