from typing import TypedDict, Optional

class LearningState(TypedDict):
    query: str
    current_topic: str
    pending_question: Optional[str]
    last_quiz_result: Optional[str]
    quiz_agent_output: Optional[str]
    learning_agent_output: Optional[str]
    research_agent_output: Optional[str]
    needs_research: bool
    router_decision: Optional[str]
