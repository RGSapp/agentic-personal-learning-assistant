import os
import re
from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq

from state import LearningState
from search_service import SearchService

ACADEMIC_SIGNALS = re.compile(
    r"\b(paper|papers|arxiv|research|study|proof|algorithm|architecture|"
    r"model|neural network|transformer|dataset|benchmark|state of the art|sota)\b",
    re.IGNORECASE,
)


class ResearchAgent:
    """
    Only invoked when the Learning agent's RAG search comes up empty
    (needs_research flag), or the student explicitly asks about something
    outside their own materials. Looks it up externally, then hands a
    grounded answer back -- it doesn't try to teach or quiz on it.

    Routes between general web search and arXiv depending on whether the
    query looks like it's after a research paper / technical deep-dive vs.
    a general concept explanation. For Raj's AI/ML coursework this matters --
    "explain gradient descent" wants a web explanation, "recent papers on
    attention mechanisms" wants arXiv.
    """

    def __init__(self, search_service: SearchService | None = None):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
        )
        self.search_service = search_service or SearchService()

    def _looks_academic(self, query: str) -> bool:
        return bool(ACADEMIC_SIGNALS.search(query))

    def search_external(self, query: str) -> str:
        """
        Runs the appropriate search(es) and returns combined raw results.
        Academic-sounding queries get arXiv results appended alongside the
        general web results, since a paper search alone can miss the plain
        explanation a student also needs.
        """
        web_results = self.search_service.search(query)

        if self._looks_academic(query):
            arxiv_results = self.search_service.search_arxiv(query)
            return f"WEB RESULTS:\n{web_results}\n\nARXIV RESULTS:\n{arxiv_results}"

        return web_results

    def __call__(self, state: LearningState) -> dict:
        query = state.get("query", "") or state.get("current_topic", "")
        raw_results = self.search_external(query)

        prompt = (
            f"The student's own study materials didn't cover this. "
            f"Using these search results, give a concise, accurate explanation. "
            f"If arXiv results are included, mention the relevant paper(s) by name.\n\n"
            f"{raw_results}\n\nTopic: {query}"
        )
        answer = self.llm.invoke(prompt).content

        return {
            "research_agent_output": answer,
            "needs_research": False,
        }

        