# main.py
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List
from rag_api.rag import RAGSystem

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app = FastAPI(title="RAG System API")

try:
    rag_system = RAGSystem()
    print("✅ RAG System initialized successfully.")
except Exception as e:
    print(f"🔴 Error initializing RAG System: {e}")
    rag_system = None

class AskRequest(BaseModel): query: str
class AskResponse(BaseModel): answer: str; pages: List[int]; sources: List[str]
class UploadResponse(BaseModel): message: str; filenames: List[str]
class DeleteRequest(BaseModel): filename: str

# In main.py, replace the entire upload_files function with this:

@app.post("/upload/", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    if not rag_system:
        raise HTTPException(status_code=500, detail="RAG System is not initialized.")
    
    filenames = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        filenames.append(file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            documents = rag_system.load_document(file_path)
            chunks = rag_system.chunk_documents(documents)
            
            #check
            if not chunks:
                # If no chunks were created
                raise HTTPException(
                    status_code=422, # Unprocessable Entity
                    detail=f"Failed to extract any text or data from '{file.filename}'. The file may be an image, empty, or corrupted."
                )
            
            rag_system.index_documents(chunks)
            
        except Exception as e:
            # Re-raise 
            raise HTTPException(status_code=500, detail=f"Failed to process file {file.filename}: {e}")

    return {"message": "Files processed successfully.", "filenames": filenames}
@app.post("/ask/", response_model=AskResponse)
async def ask_question(request: AskRequest):
    if not rag_system: raise HTTPException(status_code=500, detail="RAG System is not initialized.")
    try: return rag_system.ask_question(request.query)
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error during question answering: {e}")

@app.post("/delete_document/", status_code=200)
async def delete_document(request: DeleteRequest):
    if not rag_system: raise HTTPException(status_code=500, detail="RAG System is not initialized.")
    filename = request.filename
    file_path_to_delete = os.path.join(UPLOAD_DIR, filename)
    try:
        rag_system.delete_document(file_path_to_delete)
        if os.path.exists(file_path_to_delete): os.remove(file_path_to_delete)
        return {"message": f"Successfully deleted '{filename}' and its chunks."}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error deleting document '{filename}': {e}")