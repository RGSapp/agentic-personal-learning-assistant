import os


class SearchService:
    """
    Thin wrapper around a web search tool, kept separate so the Research
    agent doesn't care which provider is behind it.

    Uses Tavily if TAVILY_API_KEY is set (better results, built for LLM
    agents). Falls back to DuckDuckGo (no API key required) otherwise,
    """

    def __init__(self):
        self.provider = None
        self._tool = None

        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            from langchain_tavily import TavilySearch
            self._tool = TavilySearch(max_results=5, tavily_api_key=tavily_key)
            self.provider = "tavily"
        else:
            from langchain_community.tools import DuckDuckGoSearchRun
            self._tool = DuckDuckGoSearchRun()
            self.provider = "duckduckgo"

    def search(self, query: str) -> str:
        """Returns general web search results as a single formatted string."""
        try:
            result = self._tool.invoke(query)
        except Exception as e:
            return f"Search failed ({self.provider}): {e}"

        # Tavily returns a dict with a "results" list; DuckDuckGo returns a string
        if isinstance(result, dict) and "results" in result:
            formatted = []
            for r in result["results"]:
                title = r.get("title", "")
                content = r.get("content", "")
                url = r.get("url", "")
                formatted.append(f"[{title}]({url})\n{content}")
            return "\n\n".join(formatted) if formatted else "No results found."

        return str(result)

    def search_arxiv(self, query: str, max_results: int = 3) -> str:
        """
        Searches arXiv for research papers. Separate from the general web
        search because results need different formatting (title, authors,
        abstract) and this is only useful for research-paper-style queries,
        not general topic lookups.
        """
        from langchain_community.utilities import ArxivAPIWrapper

        try:
            arxiv = ArxivAPIWrapper(top_k_results=max_results, doc_content_chars_max=1500)
            result = arxiv.run(query)
        except Exception as e:
            return f"arXiv search failed: {e}"

        return result if result else "No arXiv papers found for this query."


if __name__ == "__main__":
    service = SearchService()
    print(f"Using provider: {service.provider}")
    print(service.search("time complexity of quicksort average case"))

    print("\n--- ARXIV ---")
    print(service.search_arxiv("transformer attention mechanism"))

    