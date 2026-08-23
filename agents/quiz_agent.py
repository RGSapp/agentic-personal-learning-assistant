import os
from langchain_groq import ChatGroq

from state import LearningState
from services.rag_service import RAGService


class QuizAgent:
    """
    Generates Multiple Choice Practice Questions (MCQs) on the current topic,
    grounded in the student's material via RAG, and grades the chosen option (A, B, C, D).

    Decides generate-vs-grade off state["pending_question"] -- if a question is
    already waiting on an answer, the next call grades it; otherwise it generates a new one.
    """

    def __init__(self, rag_service: RAGService | None = None):
        self.rag_service = rag_service or RAGService()
        self.llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
        )

    def generate_question(self, topic: str) -> str:
        context = self.rag_service.rag_tool(topic, k=3)
        prompt = (
            f"Based on this study material about '{topic}':\n\n{context}\n\n"
            f"Create one Multiple Choice Question (MCQ) testing understanding of this topic.\n"
            f"Requirements:\n"
            f"- Provide exactly 4 options labeled A), B), C), and D).\n"
            f"- Only one option should be correct.\n"
            f"- Do NOT reveal the correct answer or give explanations in the question text.\n"
            f"- Format clearly:\n"
            f"  [Question text]\n"
            f"  A) [Option A]\n"
            f"  B) [Option B]\n"
            f"  C) [Option C]\n"
            f"  D) [Option D]\n\n"
            f"Please respond directly with the formatted MCQ question and options."
        )
        return self.llm.invoke(prompt).content.strip()

    def grade_answer(self, topic: str, question: str, student_answer: str) -> tuple[str, str]:
        context = self.rag_service.rag_tool(topic, k=3)
        prompt = (
            f"Study material:\n{context}\n\n"
            f"Multiple Choice Question:\n{question}\n\n"
            f"Student's Answer: {student_answer}\n\n"
            f"Instructions:\n"
            f"1. Evaluate if the student's answer (e.g. option letter A, B, C, D or option text) corresponds to the correct option.\n"
            f"2. Format your response strictly starting with 'PASS:' if correct or 'FAIL:' if incorrect.\n"
            f"3. State the correct option letter clearly and provide a brief 1-2 sentence explanation based on the study material.\n\n"
            f"Example:\n"
            f"PASS: Correct! Option B is right because...\n"
            f"FAIL: Incorrect. The correct answer is Option C because..."
        )
        result = self.llm.invoke(prompt).content.strip()
        verdict = "passed" if result.upper().startswith("PASS") else "failed"
        return verdict, result

    def __call__(self, state: LearningState) -> dict:
        topic = state.get("current_topic", "")
        pending_question = state.get("pending_question")

        if pending_question:
            # a question was already asked -- this turn's message is the
            # student's attempted option selection (e.g. "A", "B", "C", "D")
            student_answer = state.get("query", "")
            verdict, feedback = self.grade_answer(topic, pending_question, student_answer)
            return {
                "last_quiz_result": verdict,
                "quiz_agent_output": feedback,
                "pending_question": None,   # clear it -- answered
            }

        # no pending question -- generate a new MCQ and hold it in state
        # until the student replies with an option
        question = self.generate_question(topic)
        return {
            "pending_question": question,
            "quiz_agent_output": question,
        }


if __name__ == "__main__":
    agent = QuizAgent()

    # simulate a full generate -> answer -> grade cycle
    state = {"current_topic": "Demand and Supply", "pending_question": None}
    result = agent(state)
    print("MCQ Question:\n", result["quiz_agent_output"])

    state.update(result)
    state["query"] = "A"
    result = agent(state)
    print("\nVerdict:", result["last_quiz_result"])
    print("Feedback:", result["quiz_agent_output"])