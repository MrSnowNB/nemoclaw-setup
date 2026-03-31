"""
SELF-HEALING RECOVERY PROTOCOL (SHRP) v1.0
Recovery Engine - Auto-Healing & Recovery Policies

Author: Cline AI Agent
Date: 2025-11-03
"""

import asyncio
import threading
import time
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass
from pathlib import Path
import json

from .shrp_logger import get_logger, EventType
from .shrp_checkpoint_manager import get_checkpoint_manager


class RecoveryStrategy(Enum):
    """Different recovery strategies available"""
    RETRY_IMMEDIATE = "retry_immediate"
    RETRY_BACKOFF = "retry_backoff"
    RESTART_SERVICE = "restart_service"
    RESTORE_CHECKPOINT = "restore_checkpoint"
    FAILOVER = "failover"
    ESCALATE_HUMAN = "escalate_human"


class FailureSeverity(Enum):
    """Severity levels for failures"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RecoveryPolicy:
    """Defines how to handle a specific type of failure"""
    failure_pattern: str  # Regex or identifier for failure type
    severity: FailureSeverity
    max_attempts: int
    backoff_multiplier: float  # For exponential backoff
    base_delay_seconds: float
    strategies: List[RecoveryStrategy]
    timeout_seconds: float
    escalate_after_attempts: int


@dataclass
class RecoveryAttempt:
    """Tracks a recovery attempt"""
    attempt_id: str
    failure_id: str
    failure_type: str
    strategy: RecoveryStrategy
    attempt_number: int
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class HealingDecision:
    """Result of recovery logic evaluation"""
    should_attempt_recovery: bool
    strategy: RecoveryStrategy
    reason: str
    confidence: float  # 0.0 to 1.0
    estimated_success_probability: float
    expected_duration_seconds: float
    requires_human_approval: bool


class SHRRecoveryEngine:
    """
    SHRP v1.0 Recovery Engine
    Implements auto-healing policies and intelligent recovery strategies
    """

    def __init__(self):
        self.logger = get_logger()
        self.checkpoint_manager = get_checkpoint_manager()

        # Recovery state
        self.recovery_policies: Dict[str, RecoveryPolicy] = {}
        self.active_recoveries: Dict[str, RecoveryAttempt] = {}
        self.failure_history: List[Dict[str, Any]] = []
        self.healing_metrics: Dict[str, Any] = {}

        # Background monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        self.monitoring_interval = 30  # seconds

        # AI-First configuration
        self.auto_healing_enabled = True
        self.human_approval_required_for_critical = True
        self.AI_agent_workflow_active = True

        # Human-in-the-loop gates
        self.human_gates = {
            "escalation_approval": False,
            "checkpoint_rollback_approval": False,
            "system_restart_approval": False
        }

        # Initialize with default policies
        self._load_default_policies()

        # Start monitoring
        self.start_monitoring()

    def _load_default_policies(self):
        """Load default recovery policies for common failures"""

        # TTS Audio generation failure
        self.recovery_policies["tts_generation_failed"] = RecoveryPolicy(
            failure_pattern="tts.*failed|audio.*null",
            severity=FailureSeverity.HIGH,
            max_attempts=3,
            backoff_multiplier=2.0,
            base_delay_seconds=5.0,
            strategies=[
                RecoveryStrategy.RETRY_IMMEDIATE,
                RecoveryStrategy.RESTART_SERVICE,
                RecoveryStrategy.ESCALATE_HUMAN
            ],
            timeout_seconds=30.0,
            escalate_after_attempts=2
        )

        # LLM API timeout/failure
        self.recovery_policies["llm_request_failed"] = RecoveryPolicy(
            failure_pattern="llm.*timeout|llm.*error|ollama.*failed",
            severity=FailureSeverity.HIGH,
            max_attempts=5,
            backoff_multiplier=1.5,
            base_delay_seconds=10.0,
            strategies=[
                RecoveryStrategy.RETRY_BACKOFF,
                RecoveryStrategy.RESTORE_CHECKPOINT,
                RecoveryStrategy.ESCALATE_HUMAN
            ],
            timeout_seconds=60.0,
            escalate_after_attempts=3
        )

        # WebSocket connection failure
        self.recovery_policies["websocket_connection_failed"] = RecoveryPolicy(
            failure_pattern="websocket.*disconnect|ws.*error",
            severity=FailureSeverity.MEDIUM,
            max_attempts=10,
            backoff_multiplier=1.2,
            base_delay_seconds=2.0,
            strategies=[
                RecoveryStrategy.RETRY_BACKOFF,
                RecoveryStrategy.RESTART_SERVICE
            ],
            timeout_seconds=120.0,
            escalate_after_attempts=7
        )

        # System resource exhaustion
        self.recovery_policies["system_resource_exhaustion"] = RecoveryPolicy(
            failure_pattern="memory.*error|cpu.*high|disk.*full",
            severity=FailureSeverity.CRITICAL,
            max_attempts=2,
            backoff_multiplier=1.0,
            base_delay_seconds=60.0,
            strategies=[
                RecoveryStrategy.RESTART_SERVICE,
                RecoveryStrategy.ESCALATE_HUMAN
            ],
            timeout_seconds=300.0,
            escalate_after_attempts=1
        )

        # Mesh network fault
        self.recovery_policies["mesh_network_fault"] = RecoveryPolicy(
            failure_pattern="mesh.*fault|network.*error",
            severity=FailureSeverity.HIGH,
            max_attempts=5,
            backoff_multiplier=2.0,
            base_delay_seconds=15.0,
            strategies=[
                RecoveryStrategy.RETRY_BACKOFF,
                RecoveryStrategy.FAILOVER,
                RecoveryStrategy.ESCALATE_HUMAN
            ],
            timeout_seconds=180.0,
            escalate_after_attempts=3
        )

    def add_recovery_policy(self, name: str, policy: RecoveryPolicy):
        """Add a custom recovery policy"""
        self.recovery_policies[name] = policy

        self.logger.log_event(
            EventType.RECOVERY_ATTEMPT,
            {
                "operation": "add_recovery_policy",
                "policy_name": name,
                "severity": policy.severity.value,
                "max_attempts": policy.max_attempts
            },
            tags=["policy", "configuration"]
        )

    def detect_failure(self, failure_type: str, error_details: Dict[str, Any],
                      context: Optional[Dict[str, Any]] = None) -> str:
        """
        Detect and initiate recovery for a failure

        Args:
            failure_type: Type of failure that occurred
            error_details: Details about the error
            context: Additional context about the failure

        Returns:
            failure_id: Unique identifier for this failure instance
        """

        failure_id = f"failure_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hash(str(error_details)) % 10000}"

        # Log the failure
        self.logger.log_event(
            EventType.SYSTEM_ERROR,
            {
                "failure_id": failure_id,
                "failure_type": failure_type,
                "error_details": error_details,
                "context": context or {}
            },
            severity="err",
            tags=["failure", "detection"]
        )

        # Store in failure history
        failure_record = {
            "failure_id": failure_id,
            "failure_type": failure_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_details": error_details,
            "context": context,
            "recovery_initiated": self.auto_healing_enabled
        }
        self.failure_history.append(failure_record)

        # Limit history size
        if len(self.failure_history) > 100:
            self.failure_history = self.failure_history[-50:]

        # Auto-initiate recovery if enabled
        if self.auto_healing_enabled:
            asyncio.create_task(self._initiate_recovery(failure_id, failure_type, error_details, context))

        return failure_id

    async def _initiate_recovery(self, failure_id: str, failure_type: str,
                                error_details: Dict[str, Any], context: Optional[Dict[str, Any]]):
        """Initiate the recovery process for a detected failure"""

        # Find applicable policy
        policy = self._find_recovery_policy(failure_type)
        if not policy:
            self.logger.log_event(
                EventType.RECOVERY_FAILED,
                {
                    "failure_id": failure_id,
                    "reason": "no_recovery_policy_found",
                    "failure_type": failure_type
                },
                tags=["recovery", "policy"]
            )
            return

        # Log recovery initiation
        self.logger.log_event(
            EventType.RECOVERY_INITIATE,
            {
                "failure_id": failure_id,
                "policy_name": self._get_policy_name(policy),
                "severity": policy.severity.value,
                "strategies": [s.value for s in policy.strategies]
            },
            tags=["recovery", "initiate"]
        )

        # Make healing decision
        decision = await self._evaluate_healing_decision(failure_id, policy, error_details, context)

        if not decision.should_attempt_recovery:
            self.logger.log_event(
                EventType.RECOVERY_FAILED,
                {
                    "failure_id": failure_id,
                    "reason": decision.reason,
                    "confidence": decision.confidence
                },
                tags=["recovery", "decision"]
            )
            return

        # Check if human approval is required
        if decision.requires_human_approval and policy.severity == FailureSeverity.CRITICAL:
            if not await self._request_human_approval(failure_id, decision):
                self.logger.log_event(
                    EventType.RECOVERY_ESCALATE,
                    {
                        "failure_id": failure_id,
                        "reason": "human_approval_denied",
                        "strategy": decision.strategy.value
                    },
                    tags=["recovery", "escalation"]
                )
                return

        # Execute recovery strategy
        await self._execute_recovery_strategy(failure_id, policy, decision)

    def _find_recovery_policy(self, failure_type: str) -> Optional[RecoveryPolicy]:
        """Find the most appropriate recovery policy for a failure type"""
        import re

        # First, try exact policy name match
        if failure_type in self.recovery_policies:
            return self.recovery_policies[failure_type]

        # Try pattern matching
        for policy in self.recovery_policies.values():
            if re.search(policy.failure_pattern, failure_type, re.IGNORECASE):
                return policy

        return None

    def _get_policy_name(self, policy: RecoveryPolicy) -> str:
        """Get the name of a recovery policy"""
        for name, p in self.recovery_policies.items():
            if p == policy:
                return name
        return "unknown_policy"

    async def _evaluate_healing_decision(self, failure_id: str, policy: RecoveryPolicy,
                                       error_details: Dict[str, Any],
                                       context: Optional[Dict[str, Any]]) -> HealingDecision:
        """
        AI-First decision making for recovery strategies
        Evaluates multiple factors to determine best recovery approach
        """

        # Count previous recovery attempts for this failure type
        recent_attempts = [
            attempt for attempt in self.active_recoveries.values()
            if attempt.failure_type == failure_id and
            (datetime.now(timezone.utc) - attempt.start_time) < timedelta(hours=1)
        ]

        attempt_count = len(recent_attempts)

        # Decision logic based on severity and history
        if policy.severity == FailureSeverity.CRITICAL:
            if attempt_count >= policy.escalate_after_attempts:
                # Escalate critical failures after max attempts
                return HealingDecision(
                    should_attempt_recovery=True,
                    strategy=RecoveryStrategy.ESCALATE_HUMAN,
                    reason="Critical failure with repeated attempts - requires human intervention",
                    confidence=1.0,
                    estimated_success_probability=0.9,
                    expected_duration_seconds=3600.0,  # 1 hour for human response
                    requires_human_approval=True
                )

            # For critical failures, prefer checkpoint restoration
            if self.checkpoint_manager.list_checkpoints():
                return HealingDecision(
                    should_attempt_recovery=True,
                    strategy=RecoveryStrategy.RESTORE_CHECKPOINT,
                    reason="Critical failure - safest approach is checkpoint restoration",
                    confidence=0.95,
                    estimated_success_probability=0.85,
                    expected_duration_seconds=120.0,
                    requires_human_approval=self.human_approval_required_for_critical
                )

        if policy.severity in [FailureSeverity.HIGH, FailureSeverity.MEDIUM]:
            if attempt_count >= policy.max_attempts:
                # Give up after max attempts
                return HealingDecision(
                    should_attempt_recovery=False,
                    strategy=RecoveryStrategy.ESCALATE_HUMAN,
                    reason="Maximum recovery attempts exceeded",
                    confidence=1.0,
                    estimated_success_probability=0.0,
                    expected_duration_seconds=0.0,
                    requires_human_approval=True
                )

            # For service restarts, check if it's been tried recently
            if RecoveryStrategy.RESTART_SERVICE in policy.strategies and attempt_count < 2:
                return HealingDecision(
                    should_attempt_recovery=True,
                    strategy=RecoveryStrategy.RESTART_SERVICE,
                    reason="Service restart often resolves high/medium severity issues",
                    confidence=0.8,
                    estimated_success_probability=0.7,
                    expected_duration_seconds=30.0,
                    requires_human_approval=False
                )

            # Try immediate retry first
            if RecoveryStrategy.RETRY_IMMEDIATE in policy.strategies and attempt_count == 0:
                return HealingDecision(
                    should_attempt_recovery=True,
                    strategy=RecoveryStrategy.RETRY_IMMEDIATE,
                    reason="First failure - try immediate retry",
                    confidence=0.9,
                    estimated_success_probability=0.6,
                    expected_duration_seconds=5.0,
                    requires_human_approval=False
                )

            # Fall back to backoff retry
            if RecoveryStrategy.RETRY_BACKOFF in policy.strategies:
                return HealingDecision(
                    should_attempt_recovery=True,
                    strategy=RecoveryStrategy.RETRY_BACKOFF,
                    reason="Multiple failures - use backoff strategy",
                    confidence=0.7,
                    estimated_success_probability=0.5,
                    expected_duration_seconds=policy.base_delay_seconds * (policy.backoff_multiplier ** attempt_count),
                    requires_human_approval=False
                )

        # Default: escape human for low severity or unknown cases
        return HealingDecision(
            should_attempt_recovery=True,
            strategy=RecoveryStrategy.ESCALATE_HUMAN,
            reason="Low confidence in automatic recovery - escalating to human",
            confidence=0.5,
            estimated_success_probability=0.8,
            expected_duration_seconds=1800.0,  # 30 minutes
            requires_human_approval=True
        )

    async def _execute_recovery_strategy(self, failure_id: str, policy: RecoveryPolicy,
                                       decision: HealingDecision):
        """Execute the chosen recovery strategy"""

        attempt_id = f"attempt_{failure_id}_{len([a for a in self.active_recoveries.values() if a.failure_id == failure_id]) + 1}"

        attempt = RecoveryAttempt(
            attempt_id=attempt_id,
            failure_id=failure_id,
            failure_type=self._get_policy_name(policy),
            strategy=decision.strategy,
            attempt_number=len([a for a in self.active_recoveries.values() if a.failure_id == failure_id]) + 1,
            start_time=datetime.now(timezone.utc)
        )

        self.active_recoveries[attempt_id] = attempt

        try:
            success = await self._perform_recovery_action(decision.strategy, failure_id, policy)
            attempt.success = success
            attempt.end_time = datetime.now(timezone.utc)

            if success:
                self.logger.log_event(
                    EventType.RECOVERY_SUCCESS,
                    {
                        "attempt_id": attempt_id,
                        "failure_id": failure_id,
                        "strategy": decision.strategy.value,
                        "duration_seconds": (attempt.end_time - attempt.start_time).total_seconds()
                    },
                    tags=["recovery", "success"]
                )
                self._update_healing_metrics(decision.strategy, True)
            else:
                # Trigger escalation for failed attempts
                await self._handle_recovery_failure(attempt, policy)

        except Exception as e:
            attempt.success = False
            attempt.error_message = str(e)
            attempt.end_time = datetime.now(timezone.utc)

            self.logger.log_event(
                EventType.RECOVERY_FAILED,
                {
                    "attempt_id": attempt_id,
                    "failure_id": failure_id,
                    "strategy": decision.strategy.value,
                    "error": str(e)
                },
                severity="err",
                tags=["recovery", "error"]
            )

        finally:
            # Clean up old attempts (keep last 50)
            if len(self.active_recoveries) > 50:
                oldest_ids = sorted(
                    self.active_recoveries.keys(),
                    key=lambda x: self.active_recoveries[x].start_time
                )[:10]  # Remove 10 oldest
                for old_id in oldest_ids:
                    del self.active_recoveries[old_id]

    async def _perform_recovery_action(self, strategy: RecoveryStrategy, failure_id: str,
                                     policy: RecoveryPolicy) -> bool:
        """Perform the actual recovery action"""

        if strategy == RecoveryStrategy.RETRY_IMMEDIATE:
            await asyncio.sleep(1.0)  # Short delay
            return await self._attempt_retry(failure_id)

        elif strategy == RecoveryStrategy.RETRY_BACKOFF:
            attempt_count = len([a for a in self.active_recoveries.values() if a.failure_id == failure_id])
            delay = policy.base_delay_seconds * (policy.backoff_multiplier ** attempt_count)
            self.logger.log_event(
                EventType.RECOVERY_ATTEMPT,
                {
                    "strategy": "retry_backoff",
                    "delay_seconds": delay,
                    "attempt_count": attempt_count
                },
                tags=["recovery", "retry"]
            )
            await asyncio.sleep(delay)
            return await self._attempt_retry(failure_id)

        elif strategy == RecoveryStrategy.RESTART_SERVICE:
            return await self._attempt_service_restart(failure_id)

        elif strategy == RecoveryStrategy.RESTORE_CHECKPOINT:
            return await self._attempt_checkpoint_restore(failure_id)

        elif strategy == RecoveryStrategy.FAILOVER:
            return await self._attempt_failover(failure_id)

        elif strategy == RecoveryStrategy.ESCALATE_HUMAN:
            return await self._attempt_human_escalation(failure_id)

        else:
            return False

    async def _attempt_retry(self, failure_id: str) -> bool:
        """Generic retry attempt - logs the attempt"""
        self.logger.log_event(
            EventType.RECOVERY_ATTEMPT,
            {"strategy": "retry", "failure_id": failure_id},
            tags=["recovery", "retry"]
        )
        # In a real implementation, this would trigger the failed operation again
        # For now, return True to simulate success
        return True

    async def _attempt_service_restart(self, failure_id: str) -> bool:
        """Attempt to restart the service"""
        try:
            self.logger.log_event(
                EventType.RECOVERY_ATTEMPT,
                {"strategy": "service_restart", "failure_id": failure_id},
                tags=["recovery", "restart"]
            )

            # This would trigger a service restart in the actual system
            # For now, just log the attempt
            await asyncio.sleep(2.0)  # Simulate restart time

            return True
        except Exception as e:
            self.logger.log_event(
                EventType.RECOVERY_FAILED,
                {"strategy": "service_restart", "failure_id": failure_id, "error": str(e)},
                severity="err",
                tags=["recovery", "restart"]
            )
            return False

    async def _attempt_checkpoint_restore(self, failure_id: str) -> bool:
        """Attempt to restore from checkpoint"""
        try:
            # Get the most recent checkpoint
            checkpoints = self.checkpoint_manager.list_checkpoints()
            if not checkpoints:
                return False

            checkpoint_id = checkpoints[0]["checkpoint_id"]
            restored_state = self.checkpoint_manager.restore_checkpoint(checkpoint_id)

            self.logger.log_event(
                EventType.RECOVERY_ATTEMPT,
                {
                    "strategy": "checkpoint_restore",
                    "failure_id": failure_id,
                    "checkpoint_id": checkpoint_id
                },
                tags=["recovery", "checkpoint"]
            )

            return True
        except Exception as e:
            self.logger.log_event(
                EventType.RECOVERY_FAILED,
                {"strategy": "checkpoint_restore", "failure_id": failure_id, "error": str(e)},
                severity="err",
                tags=["recovery", "checkpoint"]
            )
            return False

    async def _attempt_failover(self, failure_id: str) -> bool:
        """Attempt failover to backup system"""
        # Implementation would depend on the specific failover mechanism
        self.logger.log_event(
            EventType.RECOVERY_ATTEMPT,
            {"strategy": "failover", "failure_id": failure_id},
            tags=["recovery", "failover"]
        )
        return False  # Not implemented

    async def _attempt_human_escalation(self, failure_id: str) -> bool:
        """Escalate to human intervention"""
        self.logger.log_event(
            EventType.RECOVERY_ESCALATE,
            {"failure_id": failure_id, "requires_human_intervention": True},
            severity="warning",
            tags=["recovery", "escalation"]
        )
        return False  # Human intervention is required

    async def _request_human_approval(self, failure_id: str, decision: HealingDecision) -> bool:
        """Request human approval for critical recovery actions"""
        # In a real implementation, this would send notifications or create tickets
        self.logger.log_event(
            EventType.RECOVERY_ATTEMPT,
            {
                "strategy": "request_human_approval",
                "failure_id": failure_id,
                "decision": decision.strategy.value,
                "reason": decision.reason
            },
            tags=["recovery", "human_approval"]
        )

        # For now, check if any human gate is enabled
        return any(self.human_gates.values())

    async def _handle_recovery_failure(self, attempt: RecoveryAttempt, policy: RecoveryPolicy):
        """Handle failed recovery attempt"""
        self.logger.log_event(
            EventType.RECOVERY_FAILED,
            {
                "attempt_id": attempt.attempt_id,
                "failure_id": attempt.failure_id,
                "strategy": attempt.strategy.value,
                "attempt_number": attempt.attempt_number,
                "error": attempt.error_message,
                "will_escalate": attempt.attempt_number >= policy.escalate_after_attempts
            },
            severity="warning",
            tags=["recovery", "failure"]
        )

        self._update_healing_metrics(attempt.strategy, False)

        # Escalate if we've exceeded the threshold
        if attempt.attempt_number >= policy.escalate_after_attempts:
            await self._attempt_human_escalation(attempt.failure_id)

    def _update_healing_metrics(self, strategy: RecoveryStrategy, success: bool):
        """Update healing success metrics"""
        strategy_key = strategy.value
        if strategy_key not in self.healing_metrics:
            self.healing_metrics[strategy_key] = {"attempts": 0, "successes": 0}

        self.healing_metrics[strategy_key]["attempts"] += 1
        if success:
            self.healing_metrics[strategy_key]["successes"] += 1

    def get_healing_metrics(self) -> Dict[str, Any]:
        """Get current healing metrics"""
        metrics = self.healing_metrics.copy()

        # Calculate success rates
        for strategy, data in metrics.items():
            attempts = data["attempts"]
            successes = data["successes"]
            data["success_rate"] = successes / attempts if attempts > 0 else 0.0

        return metrics

    def start_monitoring(self):
        """Start background monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Perform health checks
                self._perform_health_checks()

                # Clean up old checkpoints
                self.checkpoint_manager.clear_old_checkpoints()

                time.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.log_event(
                    EventType.SYSTEM_ERROR,
                    {"component": "recovery_engine", "operation": "monitoring_loop", "error": str(e)},
                    severity="warning"
                )
                time.sleep(60)  # Wait longer after errors

    def _perform_health_checks(self):
        """Perform periodic health checks"""
        # This would integrate with system health monitoring
        # For now, just log a health check event
        self.logger.log_system_health_check(
            component="recovery_engine",
            status="healthy",
            metrics={
                "active_recoveries": len(self.active_recoveries),
                "total_failures": len(self.failure_history),
                "auto_healing_enabled": self.auto_healing_enabled
            }
        )


# Global recovery engine instance
recovery_engine = SHRRecoveryEngine()


def get_recovery_engine() -> SHRRecoveryEngine:
    """Get the global SHRP recovery engine instance"""
    return recovery_engine
