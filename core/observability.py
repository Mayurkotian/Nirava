"""Observability Module - Logging, Tracing, and Metrics

Capstone Requirement: Observability (Logging, Tracing, Metrics)

This module provides:
1. Structured logging with context
2. Agent execution tracing
3. Performance metrics collection
"""
import time
import logging
import functools
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("nirava")


@dataclass
class AgentTrace:
    """Represents a single agent execution trace."""
    agent_name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    input_summary: str = ""
    output_summary: str = ""
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, success: bool = True, error: str = None):
        """Mark trace as complete."""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.error = error


@dataclass
class PipelineMetrics:
    """Aggregated metrics for the agent pipeline."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0
    agent_latencies: Dict[str, list] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    def record(self, trace: AgentTrace):
        """Record a trace into metrics."""
        self.total_requests += 1
        if trace.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        if trace.duration_ms:
            self.total_latency_ms += trace.duration_ms
            if trace.agent_name not in self.agent_latencies:
                self.agent_latencies[trace.agent_name] = []
            self.agent_latencies[trace.agent_name].append(trace.duration_ms)

    def summary(self) -> Dict[str, Any]:
        """Return metrics summary."""
        agent_avg = {}
        for agent, latencies in self.agent_latencies.items():
            if latencies:
                agent_avg[agent] = sum(latencies) / len(latencies)
        
        return {
            "total_requests": self.total_requests,
            "success_rate": f"{self.success_rate:.1%}",
            "avg_latency_ms": f"{self.avg_latency_ms:.0f}ms",
            "agent_avg_latency": agent_avg
        }


# Global metrics instance
metrics = PipelineMetrics()


class Tracer:
    """Context manager for tracing agent execution."""
    
    def __init__(self, agent_name: str, input_data: Any = None):
        self.trace = AgentTrace(agent_name=agent_name)
        if input_data:
            self.trace.input_summary = str(input_data)[:200]
    
    def __enter__(self):
        logger.info(f"▶ {self.trace.agent_name} started")
        return self.trace
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.trace.complete(success=False, error=str(exc_val))
            logger.error(f"✖ {self.trace.agent_name} failed: {exc_val}")
        else:
            self.trace.complete(success=True)
            logger.info(f"✔ {self.trace.agent_name} completed in {self.trace.duration_ms:.0f}ms")
        
        metrics.record(self.trace)
        return False  # Don't suppress exceptions


def trace_agent(func: Callable) -> Callable:
    """Decorator to automatically trace agent methods."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        agent_name = self.__class__.__name__
        with Tracer(agent_name, args[0] if args else kwargs.get('context')):
            return func(self, *args, **kwargs)
    return wrapper


def log_context(context: Dict[str, Any], stage: str):
    """Log context at a specific pipeline stage."""
    logger.debug(f"[{stage}] Context keys: {list(context.keys())}")
    
    # Log key metrics if available
    if "metrics" in context:
        m = context["metrics"]
        logger.debug(f"[{stage}] BMI: {m.get('bmi')}, Sleep OK: {m.get('sleep_ok')}")
    
    if "insights" in context:
        logger.debug(f"[{stage}] Insights count: {len(context['insights'])}")


def get_metrics_summary() -> Dict[str, Any]:
    """Get current metrics summary for dashboard/API."""
    return metrics.summary()


# Example usage in agents:
# 
# from observability import trace_agent, Tracer, log_context
# 
# class MyAgent:
#     @trace_agent
#     def run(self, context):
#         log_context(context, "MyAgent:start")
#         # ... agent logic ...
#         return context
