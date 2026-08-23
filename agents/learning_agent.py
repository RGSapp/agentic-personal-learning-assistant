import os
from dotenv import load_dotenv
load_dotenv()

from state import LearningState
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain


class LearningAgent:
    def __init__(self, rag_service, llm=None):
        # initializing the retriever
        self.retriever = rag_service.get_retriever()

        self.llm = llm or ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=1024,
            api_key=os.getenv("GROQ_API_KEY"))


        self.system_prompt = (
            "You are an expert Learning Assistant. Your primary goal is to help the user "
            "understand concepts based ONLY on the provided document context.\n\n"
            "Depending on the user's request, apply one of the following frameworks:\n"
            "- SUMMARIZE: Provide a concise, high-level overview of the key points.\n"
            "- TEACH: Explain the concept step-by-step in accessible language, as if tutoring a student.\n"
            "- EXAMPLES: Provide concrete, real-world examples to illustrate the theory or concept.\n\n"
            "Rules:\n"
            "1. If the answer is not contained in the context, explicitly state: 'I cannot find "
            "information about this in the uploaded documents.'\n"
            "2. Do not invent facts or use outside knowledge to answer core conceptual questions.\n\n"
            "Context:\n{context}"
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}"),
        ])

        # langChain retrieval chain
        self.qa_chain = self._build_chain()

    def _build_chain(self):
        # passes the retrieved docs into the 'context' variable of the prompt
        document_chain = create_stuff_documents_chain(self.llm, self.prompt)
        # combines the retriever and the document chain
        return create_retrieval_chain(self.retriever, document_chain)

    def __call__(self, state: LearningState) -> dict:
        """
        The workflow router will call this method, passing the state.
        """
        task_query = state.get("query", "")
        print(f"[Learning Agent] Processing task: {task_query}")
        response = self.qa_chain.invoke({"input": task_query})

        # If the agent couldn't find the answer, signal for research
        answer = response["answer"]
        needs_research = False
        if "I cannot find information about this" in answer or "I don't know" in answer.lower():
            needs_research = True

        return {
            "learning_agent_output": answer,
            "needs_research": needs_research
        }

if __name__ == "__main__":
    from services.rag_service import RAGService

    # initialize rag
    rag = RAGService()

    # initialize the agent
    learning_agent = LearningAgent(rag_service=rag)

    # teaching mode
    result = learning_agent({"query": "Teach me about how an oligopoly market works.", "current_topic": "Economics", "pending_question": None})
    print("\n--- Teach Mode Response ---")
    print(result)