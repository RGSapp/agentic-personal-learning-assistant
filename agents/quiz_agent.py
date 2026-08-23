import os
from langchain_groq import ChatGroq

from state import LearningState
from services.rag_service import RAGService


class QuizAgent:
    """
    Generates practice questions on the current topic, grounded in the
    student's own material via RAG, and grades free-form answers.

    Decides generate-vs-grade off state["pending_question"] rather than
    guessing from message content -- if a question is already waiting on
    an answer, the next call grades it; otherwise it generates a new one.
    Doesn't decide mastery scores itself -- that's the Memory agent's job,
    this one just reports pass/fail for a given attempt.
    """

    def __init__(self, rag_service: RAGService | None = None):
        self.rag_service = rag_service or RAGService()
        self.llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.4,
        )

    def generate_question(self, topic: str) -> str:
        context = self.rag_service.rag_tool(topic, k=3)
        prompt = (
            f"Based on this study material about '{topic}':\n\n{context}\n\n"
            f"Write one practice question testing understanding of this topic. "
            f"Question only, no answer, no preamble."
        )
        return self.llm.invoke(prompt).content

    def grade_answer(self, topic: str, question: str, student_answer: str) -> tuple[str, str]:
        context = self.rag_service.rag_tool(topic, k=3)
        prompt = (
            f"Study material:\n{context}\n\n"
            f"Question: {question}\n"
            f"Student's answer: {student_answer}\n\n"
            f"Grade this as PASS or FAIL, then give one sentence of feedback "
            f"explaining what was right or missing. "
            f"Format exactly as: 'PASS: ...' or 'FAIL: ...'"
        )
        result = self.llm.invoke(prompt).content
        verdict = "passed" if result.strip().upper().startswith("PASS") else "failed"
        return verdict, result

    def __call__(self, state: LearningState) -> dict:
        topic = state.get("current_topic", "")
        pending_question = state.get("pending_question")

        if pending_question:
            # a question was already asked -- this turn's message is the
            # student's attempted answer
            student_answer = state.get("query", "")
            verdict, feedback = self.grade_answer(topic, pending_question, student_answer)
            return {
                "last_quiz_result": verdict,
                "quiz_agent_output": feedback,
                "pending_question": None,   # clear it -- answered
            }

        # no pending question -- generate a new one and hold it in state
        # until the student replies
        question = self.generate_question(topic)
        return {
            "pending_question": question,
            "quiz_agent_output": question,
        }


if __name__ == "__main__":
    agent = QuizAgent()

    # simulate a full generate -> answer -> grade cycle
    state = {"current_topic": "Binary Search Trees", "pending_question": None}
    result = agent(state)
    print("Question:", result["quiz_agent_output"])

    state.update(result)
    state["query"] = "It's a tree where left child is smaller and right child is larger than parent."
    result = agent(state)
    print("\nVerdict:", result["last_quiz_result"])
    print("Feedback:", result["quiz_agent_output"])