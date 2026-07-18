import os
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv() 

class RAGService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            collection_name="data_collection",
            persist_directory="./data_vector_db"
        )
        ''' #check if the vectordb already exists or not

        if os.path.exists(self.persist_directory):
            self.vector_store = Chroma(
            embedding_function=self.embeddings,
            collection_name="data_collection",
            persist_directory=self.persist_directory
            )
            print("--- Using existing vector DB ---")
        else:
            self.vector_store = Chroma(
            embedding_function=self.embeddings,
            collection_name="data_collection",
            persist_directory=self.persist_directory
            )
            print("--- Created new vector DB ---")
        '''
    def process_and_create_embeddings(self, folder_path: str = "./data") -> None:
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

    def get_retriever(self):
        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20})
        return retriever

if __name__ == "__main__":
    rag_service = RAGService()
    
    #rag_service.process_and_create_embeddings("./data") 

    retriever = rag_service.get_retriever()
    docs = retriever.invoke("What is oligopoly market?")
    
    for doc in docs:
        print(f"\nSource: {doc.metadata.get('source')}")
        print(f"Content: {doc.page_content[:200]}...")