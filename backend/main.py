import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your RAGSystem class
from rag_api.rag import RAGSystem

# Initialize FastAPI app
app = FastAPI()

# --- CORS Middleware ---
origins = [
    "http://localhost:3000",
    "localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RAG System Initialization ---
try:
    rag_system = RAGSystem()
    print("RAG System initialized successfully.")
except Exception as e:
    print(f"Error initializing RAG System: {e}")
    rag_system = None

# --- Pydantic Models for Request/Response ---
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    pages: list
    sources: list

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "RAG API is running"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not rag_system:
        raise HTTPException(status_code=500, detail="RAG System not initialized")
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File '{file.filename}' saved to '{file_path}'")
        documents = rag_system.load_document(file_path)
        if not documents:
            raise HTTPException(status_code=400, detail="Could not load document or document is empty.")
        ext = os.path.splitext(file.filename)[1].lower()
        if ext != ".pdf":
            chunks = rag_system.chunk_documents(documents)
        else:
            chunks = documents
        rag_system.index_documents(chunks)
        return {"status": "success", "filename": file.filename, "message": f"{len(chunks)} chunks indexed."}
    except Exception as e:
        print(f"Error during file upload and processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temporary file: {file_path}")

@app.post("/query", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    if not rag_system:
        raise HTTPException(status_code=500, detail="RAG System not initialized")
    try:
        result = rag_system.ask_question(request.query)
        return result
    except Exception as e:
        print(f"Error during query: {e}")
        raise HTTPException(status_code=500, detail=str(e))