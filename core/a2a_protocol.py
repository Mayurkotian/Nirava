"""A2A Protocol Implementation

Capstone Requirement: Agent-to-Agent (A2A) Protocol

This module implements Google's A2A protocol patterns for agent communication:
1. Agent Cards - Metadata describing agent capabilities
2. Message Protocol - Standardized request/response format
3. Agent Registry - Central discovery and routing
4. Task Delegation - Agents can delegate to other agents

Reference: https://github.com/google/A2A
"""
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# A2A MESSAGE PROTOCOL
# ============================================================================

class MessageType(Enum):
    """Standard A2A message types."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    DELEGATION = "delegation"
    ERROR = "error"


class TaskStatus(Enum):
    """Status of a task in the A2A protocol."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DELEGATED = "delegated"


@dataclass
class A2AMessage:
    """
    Standardized message format for A2A communication.
    
    Follows Google's A2A protocol specification.
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str = MessageType.TASK_REQUEST.value
    sender_id: str = ""
    recipient_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Task information
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""  # e.g., "health_analysis", "metric_calculation"
    
    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Response fields
    status: str = TaskStatus.PENDING.value
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "A2AMessage":
        return cls(**data)
    
    def create_response(self, result: Dict[str, Any], 
                       status: TaskStatus = TaskStatus.COMPLETED) -> "A2AMessage":
        """Create a response message to this request."""
        return A2AMessage(
            message_type=MessageType.TASK_RESPONSE.value,
            sender_id=self.recipient_id,
            recipient_id=self.sender_id,
            task_id=self.task_id,
            task_type=self.task_type,
            status=status.value,
            result=result
        )


# ============================================================================
# AGENT CARDS (Capability Declaration)
# ============================================================================

@dataclass
class AgentSkill:
    """A specific skill/capability an agent has."""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCard:
    """
    Agent Card - Metadata describing an agent's capabilities.
    
    This is the A2A mechanism for agent discovery.
    Other agents can query the registry to find agents with specific skills.
    """
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    
    # Capabilities
    skills: List[AgentSkill] = field(default_factory=list)
    supported_task_types: List[str] = field(default_factory=list)
    
    # Communication
    accepts_delegation: bool = True
    max_concurrent_tasks: int = 10
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['skills'] = [asdict(s) for s in self.skills]
        return result
    
    def has_skill(self, skill_name: str) -> bool:
        """Check if agent has a specific skill."""
        return any(s.name == skill_name for s in self.skills)
    
    def can_handle(self, task_type: str) -> bool:
        """Check if agent can handle a specific task type."""
        return task_type in self.supported_task_types


# ============================================================================
# AGENT REGISTRY (Discovery Service)
# ============================================================================

class AgentRegistry:
    """
    Central registry for A2A agent discovery.
    
    Agents register their cards here, and can query for other agents
    with specific capabilities.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
        self._handlers: Dict[str, Callable] = {}  # agent_id -> handler function
        self._message_queue: List[A2AMessage] = []
    
    def register(self, card: AgentCard, handler: Callable = None):
        """Register an agent with the registry."""
        self._agents[card.agent_id] = card
        if handler:
            self._handlers[card.agent_id] = handler
        logger.info(f"A2A: Registered agent '{card.name}' ({card.agent_id})")
    
    def unregister(self, agent_id: str):
        """Remove an agent from the registry."""
        self._agents.pop(agent_id, None)
        self._handlers.pop(agent_id, None)
    
    def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        """Get an agent's card by ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[AgentCard]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def find_by_skill(self, skill_name: str) -> List[AgentCard]:
        """Find agents that have a specific skill."""
        return [a for a in self._agents.values() if a.has_skill(skill_name)]
    
    def find_by_task_type(self, task_type: str) -> List[AgentCard]:
        """Find agents that can handle a specific task type."""
        return [a for a in self._agents.values() if a.can_handle(task_type)]
    
    def route_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Route a message to the appropriate agent and get response.
        
        This is the core A2A routing mechanism.
        """
        recipient_id = message.recipient_id
        
        if recipient_id not in self._handlers:
            logger.error(f"A2A: No handler for agent {recipient_id}")
            return A2AMessage(
                message_type=MessageType.ERROR.value,
                sender_id="registry",
                recipient_id=message.sender_id,
                task_id=message.task_id,
                error=f"Agent {recipient_id} not found or has no handler"
            )
        
        handler = self._handlers[recipient_id]
        
        try:
            logger.info(f"A2A: Routing {message.task_type} from {message.sender_id} to {recipient_id}")
            response = handler(message)
            return response
        except Exception as e:
            logger.error(f"A2A: Handler error for {recipient_id}: {e}")
            return A2AMessage(
                message_type=MessageType.ERROR.value,
                sender_id=recipient_id,
                recipient_id=message.sender_id,
                task_id=message.task_id,
                status=TaskStatus.FAILED.value,
                error=str(e)
            )


# ============================================================================
# A2A ENABLED AGENT BASE CLASS
# ============================================================================

class A2AAgent:
    """
    Base class for A2A-enabled agents.
    
    Provides standardized communication capabilities.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.card = self._create_card()
        self.registry.register(self.card, self._handle_message)
    
    def _create_card(self) -> AgentCard:
        """Override to define agent's capabilities."""
        raise NotImplementedError
    
    def _handle_message(self, message: A2AMessage) -> A2AMessage:
        """Handle incoming A2A message."""
        raise NotImplementedError
    
    def send_message(self, recipient_id: str, task_type: str, 
                    payload: Dict[str, Any]) -> A2AMessage:
        """Send a message to another agent."""
        message = A2AMessage(
            sender_id=self.card.agent_id,
            recipient_id=recipient_id,
            task_type=task_type,
            payload=payload
        )
        return self.registry.route_message(message)
    
    def delegate_task(self, skill_name: str, payload: Dict[str, Any]) -> Optional[A2AMessage]:
        """
        Delegate a task to an agent with the required skill.
        
        This is A2A task delegation - finding and routing to capable agents.
        """
        capable_agents = self.registry.find_by_skill(skill_name)
        
        if not capable_agents:
            logger.warning(f"A2A: No agent found with skill '{skill_name}'")
            return None
        
        # Select first capable agent (could implement load balancing here)
        target = capable_agents[0]
        
        logger.info(f"A2A: Delegating '{skill_name}' to {target.name}")
        
        message = A2AMessage(
            message_type=MessageType.DELEGATION.value,
            sender_id=self.card.agent_id,
            recipient_id=target.agent_id,
            task_type=skill_name,
            payload=payload
        )
        
        return self.registry.route_message(message)


# ============================================================================
# NIRAVA A2A AGENT IMPLEMENTATIONS
# ============================================================================

class A2AMetricsAgent(A2AAgent):
    """A2A-enabled Metrics Agent."""
    
    def __init__(self, registry: AgentRegistry):
        try:
            from tools.health_metrics import (
                calc_bmi, calc_bmr_mifflin, get_ideal_benchmarks
            )
            self.calc_bmi = calc_bmi
            self.calc_bmr = calc_bmr_mifflin
            self.get_benchmarks = get_ideal_benchmarks
        except ImportError:
            # Fallback implementations for demo
            self.calc_bmi = lambda w, h: round(w / ((h/100) ** 2), 1) if w and h else None
            self.calc_bmr = lambda w, h, a, s: 1500  # Stub
            self.get_benchmarks = lambda a, s: {"sleep": "7-9h", "water": "8 glasses"}
            logger.warning("Health metrics tools not available - using stubs")
        super().__init__(registry)
    
    def _create_card(self) -> AgentCard:
        return AgentCard(
            agent_id="metrics_agent",
            name="Metrics Agent",
            description="Calculates health metrics like BMI, BMR, and clinical benchmarks",
            skills=[
                AgentSkill(
                    name="calculate_bmi",
                    description="Calculate Body Mass Index",
                    input_schema={"weight_kg": "float", "height_cm": "float"},
                    output_schema={"bmi": "float", "category": "string"}
                ),
                AgentSkill(
                    name="calculate_bmr",
                    description="Calculate Basal Metabolic Rate",
                    input_schema={"weight_kg": "float", "height_cm": "float", "age": "int", "sex": "string"},
                    output_schema={"bmr": "float"}
                ),
                AgentSkill(
                    name="get_benchmarks",
                    description="Get clinical benchmarks for age/sex",
                    input_schema={"age": "int", "sex": "string"},
                    output_schema={"benchmarks": "object"}
                )
            ],
            supported_task_types=["calculate_bmi", "calculate_bmr", "get_benchmarks", "health_snapshot"]
        )
    
    def _handle_message(self, message: A2AMessage) -> A2AMessage:
        task_type = message.task_type
        payload = message.payload
        
        if task_type == "calculate_bmi":
            bmi = self.calc_bmi(payload.get("weight_kg"), payload.get("height_cm"))
            try:
                from tools.health_metrics import bmi_category
                category = bmi_category(bmi)
            except ImportError:
                category = "normal" if bmi and 18.5 <= bmi <= 25 else "check"
            result = {"bmi": bmi, "category": category}
            
        elif task_type == "calculate_bmr":
            bmr = self.calc_bmr(
                payload.get("weight_kg"),
                payload.get("height_cm"),
                payload.get("age"),
                payload.get("sex")
            )
            result = {"bmr": bmr}
            
        elif task_type == "get_benchmarks":
            benchmarks = self.get_benchmarks(payload.get("age"), payload.get("sex"))
            result = {"benchmarks": benchmarks}
            
        else:
            return message.create_response(
                {"error": f"Unknown task type: {task_type}"},
                TaskStatus.FAILED
            )
        
        return message.create_response(result, TaskStatus.COMPLETED)


class A2AResearchAgent(A2AAgent):
    """A2A-enabled Research Agent."""
    
    def __init__(self, registry: AgentRegistry):
        try:
            from agents.research_agent import ResearchAgent
            self.research_agent = ResearchAgent()
        except ImportError:
            self.research_agent = None
            logger.warning("ResearchAgent not available - using stub")
        super().__init__(registry)
    
    def _create_card(self) -> AgentCard:
        return AgentCard(
            agent_id="research_agent",
            name="Research Agent",
            description="Provides science-backed health insights with Google Search grounding",
            skills=[
                AgentSkill(
                    name="health_research",
                    description="Research health topics with grounding",
                    input_schema={"issue_type": "string", "context": "object"},
                    output_schema={"insights": "array", "sources": "array"}
                ),
                AgentSkill(
                    name="safety_check",
                    description="Check for concerning symptoms",
                    input_schema={"symptoms": "string"},
                    output_schema={"needs_professional": "bool", "level": "string"}
                )
            ],
            supported_task_types=["health_research", "safety_check"]
        )
    
    def _handle_message(self, message: A2AMessage) -> A2AMessage:
        task_type = message.task_type
        payload = message.payload
        
        if task_type == "health_research":
            if self.research_agent:
                context = self.research_agent.run(payload.get("context", {}))
                result = {
                    "insights": context.get("insights", []),
                    "sources": context.get("sources", [])
                }
            else:
                # Stub response for demo
                result = {
                    "insights": ["Sleep is important for recovery", "Hydration affects energy levels"],
                    "sources": []
                }
            
        elif task_type == "safety_check":
            if self.research_agent:
                check = self.research_agent._check_safety({"conversation_history": [
                    {"role": "user", "content": payload.get("symptoms", "")}
                ]})
                result = check
            else:
                # Stub response for demo
                result = {"needs_professional": False, "level": "normal"}
            
        else:
            return message.create_response(
                {"error": f"Unknown task type: {task_type}"},
                TaskStatus.FAILED
            )
        
        return message.create_response(result, TaskStatus.COMPLETED)


class A2AOrchestratorAgent(A2AAgent):
    """
    A2A Orchestrator - Coordinates between agents using A2A protocol.
    
    This demonstrates A2A's power: the orchestrator discovers and
    delegates to other agents based on their capabilities.
    """
    
    def __init__(self, registry: AgentRegistry):
        super().__init__(registry)
    
    def _create_card(self) -> AgentCard:
        return AgentCard(
            agent_id="orchestrator_agent",
            name="Orchestrator Agent",
            description="Coordinates health analysis by delegating to specialist agents",
            skills=[
                AgentSkill(
                    name="full_health_analysis",
                    description="Complete health analysis using all available agents",
                    input_schema={"profile": "object", "checkin": "object"},
                    output_schema={"analysis": "object"}
                )
            ],
            supported_task_types=["full_health_analysis", "coordinate"]
        )
    
    def _handle_message(self, message: A2AMessage) -> A2AMessage:
        if message.task_type == "full_health_analysis":
            return self._run_coordinated_analysis(message)
        
        return message.create_response(
            {"error": "Unknown task type"},
            TaskStatus.FAILED
        )
    
    def _run_coordinated_analysis(self, message: A2AMessage) -> A2AMessage:
        """
        Run a coordinated analysis by delegating to other agents via A2A.
        
        This is the key A2A pattern: discovering and delegating.
        """
        payload = message.payload
        profile = payload.get("profile", {})
        checkin = payload.get("checkin", {})
        
        results = {}
        
        # Step 1: Delegate to Metrics Agent (via A2A)
        metrics_response = self.delegate_task("calculate_bmi", {
            "weight_kg": profile.get("weight_kg"),
            "height_cm": profile.get("height_cm")
        })
        if metrics_response and metrics_response.status == TaskStatus.COMPLETED.value:
            results["bmi"] = metrics_response.result
        
        # Step 2: Get benchmarks (via A2A)
        benchmark_response = self.delegate_task("get_benchmarks", {
            "age": profile.get("age"),
            "sex": profile.get("sex")
        })
        if benchmark_response and benchmark_response.status == TaskStatus.COMPLETED.value:
            results["benchmarks"] = benchmark_response.result
        
        # Step 3: Delegate to Research Agent (via A2A)
        research_response = self.delegate_task("health_research", {
            "context": {"profile": profile, "checkin": checkin}
        })
        if research_response and research_response.status == TaskStatus.COMPLETED.value:
            results["research"] = research_response.result
        
        return message.create_response({
            "analysis": results,
            "agents_used": ["metrics_agent", "research_agent"],
            "coordination_method": "A2A Protocol"
        }, TaskStatus.COMPLETED)


# ============================================================================
# A2A SYSTEM SETUP
# ============================================================================

def create_a2a_system() -> tuple:
    """
    Create a complete A2A-enabled agent system.
    
    Returns:
        (registry, orchestrator) tuple
    """
    # Create central registry
    registry = AgentRegistry()
    
    # Register agents
    metrics = A2AMetricsAgent(registry)
    research = A2AResearchAgent(registry)
    orchestrator = A2AOrchestratorAgent(registry)
    
    logger.info(f"A2A System initialized with {len(registry.list_agents())} agents")
    
    return registry, orchestrator


def demo_a2a_protocol():
    """Demonstrate the A2A protocol in action."""
    print("\n" + "="*60)
    print("🔗 A2A PROTOCOL DEMONSTRATION")
    print("="*60 + "\n")
    
    # Create the A2A system
    registry, orchestrator = create_a2a_system()
    
    # List registered agents
    print("📋 Registered Agents:")
    for agent in registry.list_agents():
        skills = ", ".join([s.name for s in agent.skills])
        print(f"  • {agent.name} ({agent.agent_id})")
        print(f"    Skills: {skills}")
    print()
    
    # Demonstrate agent discovery
    print("🔍 Agent Discovery (finding agents with 'calculate_bmi' skill):")
    capable = registry.find_by_skill("calculate_bmi")
    for agent in capable:
        print(f"  ✓ {agent.name} can calculate BMI")
    print()
    
    # Demonstrate direct A2A message
    print("📨 Direct A2A Message (Orchestrator → Metrics Agent):")
    message = A2AMessage(
        sender_id="orchestrator_agent",
        recipient_id="metrics_agent",
        task_type="calculate_bmi",
        payload={"weight_kg": 70, "height_cm": 175}
    )
    response = registry.route_message(message)
    print(f"  Request: Calculate BMI for 70kg, 175cm")
    print(f"  Response: {response.result}")
    print()
    
    # Demonstrate coordinated analysis via A2A
    print("🎯 Coordinated Analysis (A2A Delegation):")
    analysis_msg = A2AMessage(
        sender_id="external",
        recipient_id="orchestrator_agent",
        task_type="full_health_analysis",
        payload={
            "profile": {"age": 30, "sex": "male", "weight_kg": 70, "height_cm": 175},
            "checkin": {"sleep_hours": 6, "stress_score": 7}
        }
    )
    result = registry.route_message(analysis_msg)
    print(f"  Agents used: {result.result.get('agents_used', [])}")
    print(f"  Coordination: {result.result.get('coordination_method', 'unknown')}")
    print(f"  BMI Result: {result.result.get('analysis', {}).get('bmi', {})}")
    print()
    
    print("="*60)
    print("✅ A2A Protocol demonstration complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    demo_a2a_protocol()
