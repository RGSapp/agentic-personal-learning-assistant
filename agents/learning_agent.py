import os
from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq # Swap with ChatOllama if running locally
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# search tool pending or this agent can be strictly based on the uploaded documents

class LearningAgent:
    def __init__(self, rag_service, llm=None):
        # initializing the retriever 
        self.retriever = rag_service.get_retriever()
        
        self.llm = llm = ChatGroq(
            model="openai/gpt-oss-20b",
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

    def process_task(self, task_query: str) -> str:
        """
        The Planner Agent will call this method, passing the specific task.
        """
        print(f"[Learning Agent] Processing task: {task_query}")
        response = self.qa_chain.invoke({"input": task_query})
        
        return response["answer"]

if __name__ == "__main__":
    from services.rag_service import RAGService

    # initialize rag
    rag = RAGService()
    
    # initialize the agent
    learning_agent = LearningAgent(rag_service=rag)

    # teaching mode
    result = learning_agent.process_task("Teach me about how an oligopoly market works.")
    print("\n--- Teach Mode Response ---")
    print(result)

    # example Mode
    result = learning_agent.process_task("Give me 3 real-world examples of an oligopoly based on the text.")
    print("\n--- Example Mode Response ---")
    print(result)
    # give i dont know response cause not in the documents