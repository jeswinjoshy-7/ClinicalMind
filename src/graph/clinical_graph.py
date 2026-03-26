import logging
import operator
import json
from dataclasses import dataclass
from typing import Annotated, List, TypedDict, Union, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END

from configs.config import settings
from src.vectorstore.store_manager import ClinicalStoreManager
from src.tools.clinical_tools import create_clinical_tools
from src.utils.safety import MedicalSafetyChecker, RiskLevel

# Configure logging
logger = logging.getLogger(__name__)


class ClinicalAgentState(TypedDict):
    """
    The state representation for the LangGraph clinical workflow.
    Tracks the conversation history and intermediate steps.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    safety_assessment: Dict[str, Any]


@dataclass
class ClinicalResponse:
    """Structured final response for the Gradio UI."""
    answer: str
    sources: List[str]
    risk_level: str


class MultiAgentClinicalGraph:
    """
    Orchestrates a multi-agent clinical reasoning workflow using LangGraph.

    The supervisor node ensures that the model always uses tools,
    cites sources, and never relies on its internal training memory
    for clinical facts.
    """

    SUPERVISOR_PROMPT = (
        "You are the ClinicalMind Supervisor, a senior clinical intelligence coordinator. "
        "Your goal is to provide accurate, evidence-based medical information.\n\n"
        "STRICT RULES:\n"
        "1. ALWAYS use the provided tools to find information. NEVER answer from your own memory.\n"
        "2. ALWAYS cite the source (filename and page) for every clinical fact you state.\n"
        "3. If multiple tools are relevant, use 'cross_reference_all'.\n"
        "4. Before providing a final answer, use 'flag_safety_concern' to validate the clinical safety.\n"
        "5. If the information is not in the database, state that you do not have that specific clinical record.\n"
        "6. Your final response must be structured, professional, and contain a 'SOURCES' section."
    )

    def __init__(self, store_manager: ClinicalStoreManager):
        """
        Initialize the graph with LLM, tools, and state machine.
        """
        self.llm = ChatGroq(
            temperature=settings.llm.temperature,
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.llm.model_name,
            max_tokens=settings.llm.max_tokens
        )

        self.tools = create_clinical_tools(store_manager)
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.safety_checker = MedicalSafetyChecker()

        # Bind tools to the LLM with parallel_tool_calls=False for better compatibility
        self.llm_with_tools = self.llm.bind_tools(self.tools, parallel_tool_calls=False)

        # Build the graph
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    def _build_graph(self) -> StateGraph:
        """Constructs the LangGraph state machine."""
        builder = StateGraph(ClinicalAgentState)

        # Define nodes
        builder.add_node("supervisor", self._call_supervisor)
        builder.add_node("tools", self._execute_tools)
        builder.add_node("safety_check", self._safety_check_node)

        # Define edges
        builder.set_entry_point("supervisor")

        # Conditional edge: decide whether to use tools, check safety, or finish
        builder.add_conditional_edges(
            "supervisor",
            self._should_continue,
            {
                "tools": "tools",
                "safety_check": "safety_check",
                "supervisor": "supervisor",  # Loop back to supervisor after tool results
                "end": END
            }
        )

        # After tools run, always go back to supervisor to process results
        builder.add_edge("tools", "supervisor")

        # After safety check, end the workflow
        builder.add_edge("safety_check", END)

        return builder

    def _should_continue(self, state: ClinicalAgentState) -> str:
        """Determines if the LLM wants to call more tools or finish."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check if this is a ToolMessage (result from tool execution)
        # After tool results, always go back to supervisor to process
        if isinstance(last_message, ToolMessage):
            return "supervisor"
        
        # Check if this is an AI message with tool calls
        if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # Execute the tools
            return "tools"
            
        # Check if this is an AI message without tool calls (final answer)
        if isinstance(last_message, AIMessage):
            return "safety_check"
            
        return "end"

    def _call_supervisor(self, state: ClinicalAgentState) -> Dict[str, Any]:
        """The core reasoning node that interacts with the LLM."""
        messages = state["messages"]

        # Inject system prompt if it's the first message
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=self.SUPERVISOR_PROMPT)] + messages

        response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def _execute_tools(self, state: ClinicalAgentState) -> Dict[str, Any]:
        """
        Node that executes tools based on the LLM's tool calls.
        Manually handles tool invocation for LangGraph 1.x compatibility.
        """
        messages = state["messages"]
        last_message = messages[-1]

        tool_outputs = []
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id")

                if tool_name in self.tools_by_name:
                    try:
                        tool = self.tools_by_name[tool_name]
                        output = tool.invoke(tool_args)
                        tool_outputs.append(
                            ToolMessage(content=output, tool_call_id=tool_id, name=tool_name)
                        )
                    except Exception as e:
                        logger.error(f"Tool execution error for {tool_name}: {e}")
                        tool_outputs.append(
                            ToolMessage(content=f"Error executing {tool_name}: {str(e)}", tool_call_id=tool_id, name=tool_name)
                        )

        return {"messages": tool_outputs}

    def _safety_check_node(self, state: ClinicalAgentState) -> Dict[str, Any]:
        """
        Node that performs safety assessment on the final response.
        Extracts the response content and runs it through the safety checker.
        """
        messages = state["messages"]

        # Find the last AI message (the final response before safety check)
        final_response = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # Check if this is a final answer (no tool calls)
                tool_calls = getattr(msg, 'tool_calls', None)
                if not tool_calls:
                    final_response = msg.content
                    break

        # Perform safety check on the response
        if final_response:
            safety_result = self.safety_checker.check_content(final_response)
            safety_assessment = {
                "risk_level": safety_result.risk_level.value,
                "is_safe": safety_result.is_safe,
                "detected_keywords": safety_result.detected_keywords,
                "disclaimer": safety_result.disclaimer
            }
            return {"safety_assessment": safety_assessment}

        return {"safety_assessment": {"risk_level": RiskLevel.LOW.value, "is_safe": True, "detected_keywords": [], "disclaimer": ""}}

    def invoke(self, query: str) -> ClinicalResponse:
        """
        Executes the clinical reasoning workflow for a given query.

        Args:
            query: The user's clinical question.

        Returns:
            A ClinicalResponse object.
        """
        inputs = {"messages": [HumanMessage(content=query)], "safety_assessment": {}}
        config = {"recursion_limit": settings.agent.recursion_limit}

        final_state = self.app.invoke(inputs, config=config)

        # Get the final AI message content (look for message without tool calls)
        final_message = None
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage):
                tool_calls = getattr(msg, 'tool_calls', None)
                if not tool_calls and msg.content:
                    final_message = msg.content
                    break

        if final_message is None:
            final_message = "Unable to generate a response. Please try again."

        # Get safety assessment from state
        safety_assessment = final_state.get("safety_assessment", {})
        risk_level = safety_assessment.get("risk_level", RiskLevel.LOW.value)

        return ClinicalResponse(
            answer=final_message,
            sources=self._extract_sources(final_state["messages"]),
            risk_level=risk_level
        )

    def _extract_sources(self, messages: List[BaseMessage]) -> List[str]:
        """Helper to extract unique sources from tool outputs in history."""
        sources = set()
        for m in messages:
            if isinstance(m, ToolMessage):
                # Extract sources from tool output
                content = m.content if isinstance(m.content, str) else str(m.content)
                for line in content.split("\n"):
                    if line.startswith("Source:"):
                        sources.add(line.replace("Source:", "").strip())
                    # Also extract from formatted search results
                    if "Source:" in line and "(Page:" in line:
                        # Extract "Source: filename (Page: X)"
                        import re
                        match = re.search(r"Source:\s*(.+?)\s*\(Page:", line)
                        if match:
                            sources.add(match.group(1).strip())
        return list(sources)
