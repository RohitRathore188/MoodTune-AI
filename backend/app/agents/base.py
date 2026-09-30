"""Base Agent Contract for Bounded AI Agents (Phase 10: AI Agent Orchestration).
Every agent satisfies:
- Clear Purpose
- Typed Input Schema & Validation
- Typed Output Schema & Validation
- Explicit Allowed Tools (no arbitrary code execution)
- Timeout & Retry Policy
- Deterministic Fallback Strategy
- Structured Logging
"""
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Optional, List, Set
from pydantic import BaseModel

logger = logging.getLogger("moodtune.agents")

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentExecutionResult(BaseModel, Generic[OutputT]):
    agent_name: str
    purpose: str
    success: bool
    proposal: OutputT
    is_fallback: bool = False
    latency_ms: float
    error_message: Optional[str] = None
    tools_invoked: List[str] = []


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for all bounded AI agents.
    Guarantees strict constraints:
    - Never executes arbitrary code
    - Restricts operations to declared allowed_tools
    - Enforces timeouts, retries, and deterministic fallbacks
    - Validates typed Pydantic inputs and outputs
    """
    def __init__(
        self,
        name: str,
        purpose: str,
        allowed_tools: Optional[List[str]] = None,
        timeout_seconds: float = 2.0,
        max_retries: int = 1
    ):
        self.name = name
        self.purpose = purpose
        self.allowed_tools: Set[str] = set(allowed_tools or [])
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"moodtune.agents.{name}")

    def verify_tool_allowed(self, tool_name: str):
        """Disallows execution of undeclared or arbitrary operations."""
        if tool_name not in self.allowed_tools:
            raise PermissionError(
                f"Agent '{self.name}' attempted to invoke disallowed tool '{tool_name}'. "
                f"Allowed tools: {list(self.allowed_tools)}"
            )

    async def run(self, input_data: InputT) -> AgentExecutionResult[OutputT]:
        start = time.perf_counter()

        # 1. Input Validation
        if not self.validate_input(input_data):
            self.logger.warning(f"[{self.name}] Input validation failed. Invoking fallback.")
            fallback_proposal = self.fallback(input_data, error="Input validation failed")
            latency = (time.perf_counter() - start) * 1000.0
            return AgentExecutionResult(
                agent_name=self.name,
                purpose=self.purpose,
                success=False,
                proposal=fallback_proposal,
                is_fallback=True,
                latency_ms=round(latency, 2),
                error_message="Input validation failed"
            )

        # 2. Execution with timeout and retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"[{self.name}] Executing purpose: {self.purpose} (attempt {attempt + 1})")
                proposal = await asyncio.wait_for(
                    self.execute(input_data),
                    timeout=self.timeout_seconds
                )
                latency = (time.perf_counter() - start) * 1000.0
                self.logger.debug(f"[{self.name}] Succeeded on attempt {attempt + 1} ({latency:.1f}ms)")
                return AgentExecutionResult(
                    agent_name=self.name,
                    purpose=self.purpose,
                    success=True,
                    proposal=proposal,
                    is_fallback=False,
                    latency_ms=round(latency, 2),
                    tools_invoked=list(self.allowed_tools)
                )
            except asyncio.TimeoutError:
                last_error = f"Execution timed out ({self.timeout_seconds}s)"
                self.logger.warning(f"[{self.name}] Attempt {attempt + 1} timed out after {self.timeout_seconds}s.")
            except PermissionError as pe:
                last_error = str(pe)
                self.logger.error(f"[{self.name}] Security violation: {pe}")
                break  # Security errors do not retry
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"[{self.name}] Attempt {attempt + 1} failed: {e}")

        # 3. Fallback execution
        latency = (time.perf_counter() - start) * 1000.0
        fallback_proposal = self.fallback(input_data, error=last_error)
        return AgentExecutionResult(
            agent_name=self.name,
            purpose=self.purpose,
            success=False,
            proposal=fallback_proposal,
            is_fallback=True,
            latency_ms=round(latency, 2),
            error_message=last_error
        )

    def validate_input(self, input_data: InputT) -> bool:
        """Validates that input is a valid Pydantic model instance."""
        return isinstance(input_data, BaseModel)

    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """Core execution logic returning a structured proposal."""
        pass

    @abstractmethod
    def fallback(self, input_data: InputT, error: Optional[str] = None) -> OutputT:
        """Deterministic fallback proposal when execution fails or times out."""
        pass
