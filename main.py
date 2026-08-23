import os
from dotenv import load_dotenv
load_dotenv()
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from state import LearningState
from workflow import workflow, rag_service

DATA_DIR = "./data"

app = FastAPI(
    title="Agentic Personal Learning Assistant API",
    description="API for routing queries to Learning, Quiz, and Research agents."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx"}


@app.get("/")
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Agentic Personal Learning Assistant API is running"}


class ChatRequest(BaseModel):
    query: str
    current_topic: str = "General"
    pending_question: Optional[str] = None


class ChatResponse(BaseModel):
    state: dict
    output: str


class UploadResponse(BaseModel):
    uploaded: List[str]
    failed: List[str]
    total_chunks: int
    message: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
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

        final_state = workflow.invoke(initial_state)

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


@app.post("/upload", response_model=UploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Accept one or more documents, save them to ./data/, and ingest them
    into the Chroma vector store. Supported: PDF, TXT, DOCX.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    saved_paths: List[str] = []
    failed: List[str] = []

    for upload in files:
        name = upload.filename or "unnamed"
        ext = os.path.splitext(name)[1].lower()

        if ext not in SUPPORTED_EXTENSIONS:
            failed.append(f"{name} (unsupported type '{ext}')")
            continue

        dest = os.path.join(DATA_DIR, name)
        try:
            with open(dest, "wb") as f:
                shutil.copyfileobj(upload.file, f)
            saved_paths.append(dest)
        except Exception as e:
            failed.append(f"{name} (save error: {e})")
        finally:
            await upload.close()

    total_chunks = 0
    if saved_paths:
        try:
            total_chunks = rag_service.ingest_files(saved_paths)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    uploaded_names = [os.path.basename(p) for p in saved_paths]
    message = (
        f"Successfully indexed {len(uploaded_names)} file(s) ({total_chunks} chunks)."
        if uploaded_names else "No files were ingested."
    )
    if failed:
        message += f" Failed: {', '.join(failed)}."

    return UploadResponse(
        uploaded=uploaded_names,
        failed=failed,
        total_chunks=total_chunks,
        message=message
    )


@app.get("/documents", response_model=List[str])
async def list_documents():
    """Return a list of unique document names currently indexed in the vector store."""
    try:
        return rag_service.get_document_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting FastAPI server on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

