"""
SELF-HEALING RECOVERY PROTOCOL (SHRP) v1.0
Event Emitter - Comprehensive Event Emission for SHRP Operations

Author: Cline AI Agent
Date: 2025-11-03
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
import json

from .shrp_logger import get_logger, EventType


class EventPriority(Enum):
    """Priority levels for event processing"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventFilter:
    """Filter for event subscribers"""

    def __init__(self, event_types: Optional[List[EventType]] = None,
                 tags: Optional[List[str]] = None,
                 min_severity: Optional[str] = None,
                 source_components: Optional[List[str]] = None):
        self.event_types = event_types or []
        self.tags = tags or []
        self.min_severity = min_severity
        self.source_components = source_components or []

    def matches(self, event_data: Dict[str, Any], shrp_data: Dict[str, Any]) -> bool:
        """Check if event matches this filter"""

        # Check event type
        if self.event_types:
            event_type = shrp_data.get("event_type")
            if not event_type or event_type not in [et.value for et in self.event_types]:
                return False

        # Check tags
        if self.tags:
            event_tags = shrp_data.get("tags", [])
            if not any(tag in self.tags for tag in event_tags):
                return False

        # Check severity
        if self.min_severity:
            severity = shrp_data.get("severity", "info")
            severity_levels = {"debug": 0, "info": 1, "notice": 2, "warning": 3, "err": 4, "crit": 5, "alert": 6, "emerg": 7}
            min_level = severity_levels.get(self.min_severity, 1)
            event_level = severity_levels.get(severity, 1)
            if event_level < min_level:
                return False

        # Check source component
        if self.source_components:
            app_name = event_data.get("app_name")
            if app_name not in self.source_components:
                return False

        return True


class EventSubscriber:
    """Represents an event subscriber"""

    def __init__(self, callback: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]],
                 filter: EventFilter,
                 name: str,
                 priority: EventPriority = EventPriority.NORMAL,
                 max_queue_size: int = 1000):
        self.callback = callback
        self.filter = filter
        self.name = name
        self.priority = priority
        self.max_queue_size = max_queue_size
        self.is_active = True
        self.processed_events = 0
        self.failed_events = 0
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)

    async def process_event(self, event_data: Dict[str, Any], shrp_data: Dict[str, Any]):
        """Process an event if it matches the filter"""
        if not self.is_active or not self.filter.matches(event_data, shrp_data):
            return

        try:
            if self.queue.full():
                # Drop oldest event if queue is full
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            await self.queue.put((event_data, shrp_data))

            # Process the event
            if not self.queue.empty():
                event_data, shrp_data = await self.queue.get()
                await self.callback(event_data, shrp_data)
                self.processed_events += 1

        except Exception as e:
            self.failed_events += 1
            # In a real system, we'd log this failure
            print(f"Event subscriber {self.name} failed to process event: {e}")


class SHRPEventEmitter:
    """
    SHRP v1.0 Event Emitter
    Handles comprehensive event emission and subscription system
    """

    def __init__(self):
        self.logger = get_logger()

        # Subscription management
        self.subscribers: List[EventSubscriber] = []
        self.subscriber_lock = threading.Lock()

        # Event processing
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="shrp-event")
        self.event_loop = asyncio.new_event_loop()
        self.processing_thread: Optional[threading.Thread] = None
        self.is_running = False

        # Event statistics
        self.emitted_events = 0
        self.delivered_events = 0
        self.failed_deliveries = 0

        # Built-in event handlers for SHRP components
        self._setup_builtin_handlers()

        # Start processing thread
        self.start()

    def _setup_builtin_handlers(self):
        """Set up built-in event handlers for SHRP operations"""

        # System health monitoring handler
        async def handle_system_health(event_data: Dict[str, Any], shrp_data: Dict[str, Any]):
            """Handle system health events"""
            if shrp_data.get("event_type") == EventType.SYSTEM_HEALTH_CHECK.value:
                # Could integrate with external monitoring systems
                health_data = event_data.get("data", {})
                component = health_data.get("component")
                status = health_data.get("status")

                if status != "healthy":
                    # Escalation logic could be implemented here
                    pass

        # Recovery event handler
        async def handle_recovery_events(event_data: Dict[str, Any], shrp_data: Dict[str, Any]):
            """Handle recovery-related events"""
            event_type = shrp_data.get("event_type")
            if event_type and event_type.startswith("recovery."):
                recovery_data = event_data.get("data", {})
                # Could trigger additional healing actions or notifications
                pass

        # LLM event handler
        async def handle_llm_events(event_data: Dict[str, Any], shrp_data: Dict[str, Any]):
            """Handle LLM-related events"""
            event_type = shrp_data.get("event_type")
            if event_type and event_type.startswith("llm."):
                llm_data = event_data.get("data", {})
                # Could implement LLM failover or rate limiting
                pass

        # Add built-in subscribers
        self.subscribe(
            callback=handle_system_health,
            filter=EventFilter(event_types=[EventType.SYSTEM_HEALTH_CHECK]),
            name="system_health_monitor"
        )

        self.subscribe(
            callback=handle_recovery_events,
            filter=EventFilter(event_types=[
                EventType.RECOVERY_INITIATE, EventType.RECOVERY_SUCCESS,
                EventType.RECOVERY_FAILED, EventType.RECOVERY_ESCALATE
            ]),
            name="recovery_monitor"
        )

        self.subscribe(
            callback=handle_llm_events,
            filter=EventFilter(event_types=[
                EventType.LLM_REQUEST, EventType.LLM_RESPONSE,
                EventType.LLM_ERROR, EventType.LLM_TIMEOUT
            ]),
            name="llm_monitor"
        )

    def subscribe(self, callback: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]],
                  filter: EventFilter,
                  name: str,
                  priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        Subscribe to events

        Args:
            callback: Async function to handle events
            filter: Event filter for this subscriber
            name: Unique name for this subscriber
            priority: Processing priority

        Returns:
            subscriber_id: Unique identifier for the subscription
        """

        subscriber = EventSubscriber(callback, filter, name, priority)

        with self.subscriber_lock:
            # Remove existing subscriber with same name
            self.subscribers = [s for s in self.subscribers if s.name != name]
            self.subscribers.append(subscriber)

        self.logger.log_event(
            EventType.SYSTEM_INFO,
            {
                "operation": "event_subscriber_added",
                "subscriber_name": name,
                "priority": priority.value,
                "filter": {
                    "event_types": [et.value for et in filter.event_types] if filter.event_types else [],
                    "tags": filter.tags,
                    "min_severity": filter.min_severity,
                    "source_components": filter.source_components
                }
            },
            tags=["event", "subscription"]
        )

        return name

    def unsubscribe(self, subscriber_name: str) -> bool:
        """Remove a subscriber"""
        with self.subscriber_lock:
            original_count = len(self.subscribers)
            self.subscribers = [s for s in self.subscribers if s.name != subscriber_name]

            removed = len(self.subscribers) < original_count
            if removed:
                self.logger.log_event(
                    EventType.SYSTEM_INFO,
                    {"operation": "event_subscriber_removed", "subscriber_name": subscriber_name},
                    tags=["event", "subscription"]
                )

            return removed

    async def emit_event_async(self, event_data: Dict[str, Any],
                              shrp_data: Dict[str, Any],
                              priority: EventPriority = EventPriority.NORMAL) -> int:
        """
        Emit an event to all matching subscribers (async version)

        Args:
            event_data: Full event data
            shrp_data: SHRP-specific event data
            priority: Event processing priority

        Returns:
            delivered_count: Number of subscribers that received the event
        """

        delivered_count = 0
        tasks = []

        # Get subscribers based on priority
        priority_subscribers = []
        with self.subscriber_lock:
            for subscriber in self.subscribers:
                if subscriber.is_active and subscriber.priority == priority:
                    priority_subscribers.append(subscriber)

        # Deliver to matching subscribers
        for subscriber in priority_subscribers:
            try:
                task = asyncio.create_task(subscriber.process_event(event_data, shrp_data))
                tasks.append(task)
                delivered_count += 1
            except Exception as e:
                self.failed_deliveries += 1
                print(f"Failed to deliver event to subscriber {subscriber.name}: {e}")

        # Wait for all deliveries (with timeout)
        if tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True),
                                     timeout=30.0)
            except asyncio.TimeoutError:
                print("Event delivery timeout")

        # Update statistics
        self.emitted_events += 1
        self.delivered_events += delivered_count

        return delivered_count

    def emit_event(self, event_data: Dict[str, Any],
                   shrp_data: Dict[str, Any],
                   priority: EventPriority = EventPriority.NORMAL) -> int:
        """
        Emit an event to all matching subscribers

        Args:
            event_data: Full event data
            shrp_data: SHRP-specific event data
            priority: Event processing priority

        Returns:
            delivered_count: Number of subscribers that received the event
        """

        # Run async emission in event loop
        if self.event_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self.emit_event_async(event_data, shrp_data, priority),
                self.event_loop
            )
            try:
                return future.result(timeout=5.0)
            except Exception as e:
                print(f"Event emission failed: {e}")
                return 0
        else:
            # Fallback for when event loop isn't running
            async def sync_emit():
                return await self.emit_event_async(event_data, shrp_data, priority)

            try:
                return asyncio.run(sync_emit())
            except Exception as e:
                print(f"Event emission failed: {e}")
                return 0

    def emit_task_event(self, task_id: str, event_type: EventType,
                       task_name: str, data: Optional[Dict[str, Any]] = None,
                       task_metadata: Optional[Dict[str, Any]] = None):
        """Emit a task-related event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "task_name": task_name,
                **(data or {})
            },
            task_id=task_id,
            tags=["task"]
        )

        # Add task metadata to context
        if task_metadata:
            event_data["context"]["task_metadata"] = task_metadata

        self.emit_event(event_data, shrp_data)

    def emit_checkpoint_event(self, event_type: EventType,
                             checkpoint_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a checkpoint-related event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "checkpoint_id": checkpoint_id,
                **(data or {})
            },
            tags=["checkpoint"]
        )

        self.emit_event(event_data, shrp_data)

    def emit_recovery_event(self, event_type: EventType,
                           failure_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a recovery-related event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "failure_id": failure_id,
                **(data or {})
            },
            tags=["recovery"]
        )

        self.emit_event(event_data, shrp_data, EventPriority.HIGH)

    def emit_llm_event(self, event_type: EventType,
                      request_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit an LLM-related event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "request_id": request_id,
                **(data or {})
            },
            correlation_id=request_id,
            tags=["llm"]
        )

        self.emit_event(event_data, shrp_data)

    def emit_tts_event(self, event_type: EventType,
                      audio_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a TTS-related event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "audio_id": audio_id,
                **(data or {})
            },
            correlation_id=audio_id,
            tags=["tts"]
        )

        # Use HIGH priority for TTS errors
        priority = EventPriority.HIGH if event_type == EventType.TTS_ERROR else EventPriority.NORMAL
        self.emit_event(event_data, shrp_data, priority)

    def emit_websocket_event(self, event_type: EventType,
                           client_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a WebSocket-related event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "client_id": client_id,
                **(data or {})
            },
            tags=["websocket"]
        )

        self.emit_event(event_data, shrp_data)

    def emit_session_event(self, event_type: EventType,
                          session_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a session-related event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "session_id": session_id,
                **(data or {})
            },
            session_id=session_id,
            tags=["session"]
        )

        self.emit_event(event_data, shrp_data)

    def emit_terminal_event(self, event_type: EventType,
                           command_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a terminal operation event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "command_id": command_id,
                **(data or {})
            },
            correlation_id=command_id,
            tags=["terminal"]
        )

        # Use HIGH priority for terminal errors
        priority = EventPriority.HIGH if "error" in event_type.value else EventPriority.NORMAL
        self.emit_event(event_data, shrp_data, priority)

    def emit_mesh_event(self, event_type: EventType,
                       node_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a mesh network event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "node_id": node_id,
                **(data or {})
            },
            tags=["mesh"]
        )

        # Use CRITICAL priority for mesh faults
        priority = EventPriority.CRITICAL if "fault" in event_type.value else EventPriority.NORMAL
        self.emit_event(event_data, shrp_data, priority)

    def emit_mode_event(self, event_type: EventType,
                       session_id: str, data: Optional[Dict[str, Any]] = None):
        """Emit a mode switching event"""
        event_data, shrp_data = self._build_event(
            event_type,
            {
                "session_id": session_id,
                **(data or {})
            },
            session_id=session_id,
            tags=["mode"]
        )

        self.emit_event(event_data, shrp_data, EventPriority.HIGH)

    def _build_event(self, event_type: EventType, data: Dict[str, Any],
                    severity: str = "info", session_id: Optional[str] = None,
                    task_id: Optional[str] = None, correlation_id: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> tuple:
        """Build event data structures"""

        # Use logger to create the event (this will also write to logs)
        event_id = self.logger.log_event(
            event_type,
            data,
            severity=severity,
            session_id=session_id,
            task_id=task_id,
            correlation_id=correlation_id,
            tags=tags
        )

        # Reconstruct the event data (this would normally come from the logger)
        # In production, the logger would return the full event structure
        event_data = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "app_name": "alice-cyberland",
            "data": data,
            "context": self.logger.event_context.copy()
        }

        shrp_data = {
            "version": "1.0",
            "event_type": event_type.value,
            "event_id": event_id,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "tags": tags or []
        }

        if session_id:
            shrp_data["session_id"] = session_id
        if task_id:
            shrp_data["task_id"] = task_id
        if correlation_id:
            shrp_data["correlation_id"] = correlation_id

        return event_data, shrp_data

    def get_stats(self) -> Dict[str, Any]:
        """Get event emitter statistics"""
        with self.subscriber_lock:
            subscriber_stats = {
                s.name: {
                    "processed_events": s.processed_events,
                    "failed_events": s.failed_events,
                    "queue_size": s.queue.qsize(),
                    "is_active": s.is_active,
                    "priority": s.priority.value
                }
                for s in self.subscribers
            }

        return {
            "emitted_events": self.emitted_events,
            "delivered_events": self.delivered_events,
            "failed_deliveries": self.failed_deliveries,
            "active_subscribers": len([s for s in self.subscribers if s.is_active]),
            "subscriber_stats": subscriber_stats
        }

    def start(self):
        """Start the event processing system"""
        if self.is_running:
            return

        def run_event_loop():
            """Run the event loop in a separate thread"""
            try:
                asyncio.set_event_loop(self.event_loop)
                self.event_loop.run_forever()
            except Exception as e:
                print(f"Event loop error: {e}")
            finally:
                self.event_loop.close()

        self.processing_thread = threading.Thread(target=run_event_loop, daemon=True)
        self.processing_thread.start()
        self.is_running = True

        self.logger.log_event(
            EventType.SYSTEM_INFO,
            {"operation": "event_emitter_started"},
            tags=["event", "emitter"]
        )

    def stop(self):
        """Stop the event processing system"""
        if not self.is_running:
            return

        self.is_running = False
        if self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)

        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)

        self.executor.shutdown(wait=True)

        self.logger.log_event(
            EventType.SYSTEM_INFO,
            {"operation": "event_emitter_stopped"},
            tags=["event", "emitter"]
        )


# Global event emitter instance
event_emitter = SHRPEventEmitter()


def get_event_emitter() -> SHRPEventEmitter:
    """Get the global SHRP event emitter instance"""
    return event_emitter
