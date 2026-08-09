from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

from state import LearningState
from workflow import workflow

app = FastAPI(
    title="Agentic Personal Learning Assistant API",
    description="API for routing queries to Learning, Quiz, and Research agents."
)

class ChatRequest(BaseModel):
    query: str
    current_topic: str = "General"
    pending_question: Optional[str] = None
    
class ChatResponse(BaseModel):
    state: dict
    output: str
    
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Initialize state
        initial_state: LearningState = {
            "query": request.query,
            "current_topic": request.current_topic,
            "pending_question": request.pending_question,
            "last_quiz_result": None,
            "quiz_agent_output": None,
            "learning_agent_output": None,
            "research_agent_output": None,
            "needs_research": False,
            "router_decision": None
        }
        
        # Run workflow
        final_state = workflow.invoke(initial_state)
        
        # Determine the final output message
        output = ""
        if final_state.get("router_decision") == "learning":
            output = final_state.get("learning_agent_output", "")
            if final_state.get("needs_research"):
                output += "\n\n(Fallback to Research): " + final_state.get("research_agent_output", "")
        elif final_state.get("router_decision") == "quiz":
            output = final_state.get("quiz_agent_output", "")
            if final_state.get("last_quiz_result"):
                output = f"Result: {final_state.get('last_quiz_result')}\nFeedback: {output}"
        elif final_state.get("router_decision") == "research":
            output = final_state.get("research_agent_output", "")
            
        return ChatResponse(state=final_state, output=output)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
