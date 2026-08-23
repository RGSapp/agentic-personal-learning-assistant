import os
from dotenv import load_dotenv
from typing import List

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

load_dotenv()


class RAGService:
    def __init__(self):
        self.embeddings = FastEmbedEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            collection_name="data_collection",
            persist_directory="./data_vector_db"
        )

    def _load_file(self, file_path: str):
        """Load a single file based on its extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        return loader.load()

    def ingest_files(self, file_paths: List[str]) -> int:
        """
        Ingest a specific list of files into the vector store.
        Only embeds the given files — avoids re-embedding the entire ./data folder.
        Returns the number of chunks added.
        """
        all_docs = []
        for path in file_paths:
            try:
                docs = self._load_file(path)
                all_docs.extend(docs)
                print(f"[RAGService] Loaded: {path} ({len(docs)} pages/sections)")
            except Exception as e:
                print(f"[RAGService] Failed to load {path}: {e}")

        if not all_docs:
            return 0

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(all_docs)
        self.vector_store.add_documents(chunks)
        print(f"[RAGService] Added {len(chunks)} chunks from {len(file_paths)} file(s).")
        return len(chunks)

    def process_and_create_embeddings(self, folder_path: str = "./data") -> None:
        """Scan an entire folder and embed all PDFs (legacy method)."""
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"The directory {folder_path} does not exist.")

        print(f"Scanning and loading PDFs from: {folder_path}...")

        loader = DirectoryLoader(
            path=folder_path,
            glob="*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True
        )
        pages = loader.load()
        print(f"Successfully loaded {len(pages)} total pages. Splitting into chunks...")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(pages)
        print(f"Adding {len(chunks)} chunks to Chroma vector store...")
        self.vector_store.add_documents(chunks)
        print("--------------VECTOR DB IS READY---------------")

    def get_document_list(self) -> List[str]:
        """
        Return a sorted list of unique source document basenames
        currently stored in the vector store.
        """
        try:
            result = self.vector_store.get(include=["metadatas"])
            metadatas = result.get("metadatas", [])
            sources = set()
            for meta in metadatas:
                src = meta.get("source") or meta.get("file_path") or ""
                if src:
                    sources.add(os.path.basename(src))
            return sorted(sources)
        except Exception as e:
            print(f"[RAGService] Could not fetch document list: {e}")
            return []

    def rag_tool(self, query: str, k: int = 5) -> str:
        """
        Convenience method used by quiz/learning agents: retrieves top-k
        relevant chunks and returns them as a single concatenated string.
        """
        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": 20}
        )
        docs = retriever.invoke(query)
        return "\n\n".join(doc.page_content for doc in docs)

    def get_retriever(self):
        return self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20}
        )


if __name__ == "__main__":
    rag_service = RAGService()
    retriever = rag_service.get_retriever()
    docs = retriever.invoke("What is oligopoly market?")
    for doc in docs:
        print(f"\nSource: {doc.metadata.get('source')}")
        print(f"Content: {doc.page_content[:200]}...")