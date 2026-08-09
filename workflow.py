import os
from typing import Dict, Any, Literal
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from state import LearningState
from agents.learning_agent import LearningAgent
from agents.quiz_agent import QuizAgent
from agents.research_agent import ResearchAgent
from services.rag_service import RAGService
from services.search_service import SearchService

# Initialize shared services
rag_service = RAGService()
search_service = SearchService()

# Initialize agents
learning_agent = LearningAgent(rag_service)
quiz_agent = QuizAgent(rag_service)
research_agent = ResearchAgent(search_service)

# Initialize router LLM
router_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
)

class RouteDecision(BaseModel):
    decision: Literal["learning", "quiz", "research"] = Field(
        description="The next step in the workflow based on the user's intent."
    )

def router_node(state: LearningState) -> dict:
    query = state.get("query", "").lower()
    
    # If there's a pending question, we MUST go to the quiz agent to grade it
    if state.get("pending_question"):
        return {"router_decision": "quiz"}
        
    # Otherwise, classify intent
    prompt = f"""
    You are an intelligent router for a learning assistant.
    Analyze the user query: "{query}"
    
    Classify the intent into one of three categories:
    1. 'quiz': The user is asking to be tested, quizzed, or generated practice questions.
    2. 'research': The user is explicitly asking to search the web, papers, or find external information not in their notes.
    3. 'learning': The user wants an explanation, summary, or examples (default behavior).
    """
    
    # Simple keyword fallback before LLM (optional, but saves tokens)
    if "quiz" in query or "test me" in query or "practice" in query:
        decision = "quiz"
    elif "research" in query or "search web" in query or "arxiv" in query:
        decision = "research"
    else:
        # Use LLM for harder routing
        structured_llm = router_llm.with_structured_output(RouteDecision)
        result = structured_llm.invoke([HumanMessage(content=prompt)])
        decision = result.decision
        
    return {"router_decision": decision}

def route_edges(state: LearningState) -> str:
    # Read the decision from the router
    decision = state.get("router_decision")
    if decision == "learning":
        return "learning"
    elif decision == "quiz":
        return "quiz"
    elif decision == "research":
        return "research"
    return "learning"

def research_fallback_edge(state: LearningState) -> str:
    # If learning agent couldn't find the answer in RAG, fallback to research
    if state.get("needs_research", False):
        return "research"
    return END

# Build Graph
graph_builder = StateGraph(LearningState)

# Add Nodes
graph_builder.add_node("router", router_node)
graph_builder.add_node("learning", learning_agent)
graph_builder.add_node("quiz", quiz_agent)
graph_builder.add_node("research", research_agent)

# Set Entry Point
graph_builder.set_entry_point("router")

# Add Conditional Edges from Router
graph_builder.add_conditional_edges(
    "router",
    route_edges,
    {
        "learning": "learning",
        "quiz": "quiz",
        "research": "research"
    }
)

# Add Conditional Edges from Learning Agent
graph_builder.add_conditional_edges(
    "learning",
    research_fallback_edge,
    {
        "research": "research",
        END: END
    }
)

# Other agents just end
graph_builder.add_edge("quiz", END)
graph_builder.add_edge("research", END)

# Compile Graph
workflow = graph_builder.compile()
