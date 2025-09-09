import os
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import TextLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pymupdf
from langchain.docstore.document import Document
import concurrent.futures
import re
from typing import List, Dict, Any
import pandas as pd

load_dotenv()

# --- Helper functions for multiprocessing ---
def flatten_table(table_data):
    if not table_data or len(table_data) < 2:
        return []
    headers = [str(h).strip() for h in table_data[0]]
    flattened_rows = []
    for row in table_data[1:]:
        subject = str(row[0]).strip()
        if not subject:
            continue
        for i, cell in enumerate(row[1:]):
            cell_text = str(cell).strip()
            if i + 1 < len(headers):
                header = headers[i + 1]
                if cell_text and header:
                    sentence = f"For the benefit '{subject}', the value under '{header}' is '{cell_text}'."
                    flattened_rows.append(sentence)
    return flattened_rows

def group_clauses(text: str) -> list[str]:
    pattern = r'(\n\d+\)\s.*?\(Code\s-\w+\)|\n[a-z]\.\s)'
    parts = re.split(pattern, text)
    grouped_clauses = []
    if parts[0] and parts[0].strip():
        grouped_clauses.append(parts[0].strip())
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            heading = parts[i].strip()
            content = parts[i+1].strip()
            grouped_clauses.append(f"{heading}\n{content}")
        else:
            grouped_clauses.append(parts[i].strip())
    return [clause for clause in grouped_clauses if clause]

def process_pdf_page(page_data):
    page_num, pdf_path = page_data
    doc = pymupdf.open(pdf_path)
    page = doc.load_page(page_num)
    processed_units = []
    tables = page.find_tables()
    for table in tables:
        table_data = table.extract()
        flattened_sentences = flatten_table(table_data)
        for sentence in flattened_sentences:
            processed_units.append(Document(page_content=sentence, metadata={'page': page_num + 1, 'type': 'table', 'source': pdf_path}))
    text = page.get_text()
    for table in tables:
        text = text.replace(page.get_text(clip=table.bbox), "")
    clauses = group_clauses(text)
    for clause in clauses:
        processed_units.append(Document(page_content=clause, metadata={'page': page_num + 1, 'type': 'clause', 'source': pdf_path}))
    doc.close()
    return processed_units
# --- End of Helper Functions ---

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY environment variable not set.")
if not PINECONE_API_KEY:
    print("Warning: PINECONE_API_KEY environment variable not set.")


class RAGSystem:
    def __init__(self, pinecone_index_name: str = "policy-document-index", chunk_size: int = 1000, chunk_overlap: int = 100):
        self.pinecone_index_name = pinecone_index_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=GOOGLE_API_KEY)
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self._initialize_pinecone_index()
        self.vector_store = self._initialize_vector_store()
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=GOOGLE_API_KEY)

    def _initialize_pinecone_index(self):
        if self.pinecone_index_name not in self.pc.list_indexes().names():
            print(f"Creating a new serverless index: {self.pinecone_index_name}")
            self.pc.create_index(
                name=self.pinecone_index_name,
                dimension=768,
                metric="cosine",
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
        print(f"Pinecone index '{self.pinecone_index_name}' is ready.")

    def _initialize_vector_store(self):
        return PineconeVectorStore(index_name=self.pinecone_index_name, embedding=self.embeddings)

    def load_document(self, file_path: str) -> List[Document]:
        ext = os.path.splitext(file_path)[1].lower()
        documents = []
        if ext == ".pdf":
            print(f"Loading PDF: {file_path}")
            try:
                doc = pymupdf.open(file_path)
                pages_to_process = [(i, file_path) for i in range(len(doc))]
                doc.close()
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    results = executor.map(process_pdf_page, pages_to_process)
                    for result in results:
                        documents.extend(result)
            except Exception as e:
                print(f"Error loading PDF file {file_path}: {e}")
        elif ext == ".txt":
            print(f"Loading Text: {file_path}")
            try:
                loader = TextLoader(file_path)
                documents = loader.load()
                for doc in documents:
                    doc.metadata['source'] = file_path
            except Exception as e:
                print(f"Error loading Text file {file_path}: {e}")
        elif ext in [".xls", ".xlsx"]:
            print(f"Loading Excel: {file_path}")
            try:
                df = pd.read_excel(file_path)
                text_content = df.to_string()
                documents.append(Document(page_content=text_content, metadata={'source': file_path, 'type': 'excel'}))
            except Exception as e:
                print(f"Error loading Excel file {file_path}: {e}")
        return documents

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        print("Chunking documents...")
        if not documents:
            print("No documents to chunk.")
            return []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks.")
        return chunks

    def index_documents(self, documents: List[Document]):
        if not documents:
            print("No documents to index.")
            return
        print(f"Indexing {len(documents)} document chunks...")
        self.vector_store.add_documents(documents)
        print("Indexing complete.")

    def ask_question(self, query: str) -> Dict[str, Any]:
        print("Retrieving relevant context...")
        if not self.vector_store:
            return {"answer": "RAG system not initialized. Please upload documents first.", "pages": [], "sources": []}
        retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        retrieved_docs = retriever.invoke(query)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        page_numbers = sorted(list(set([doc.metadata.get('page') for doc in retrieved_docs if doc.metadata.get('page')])))
        sources = sorted(list(set([doc.metadata.get('source') for doc in retrieved_docs if doc.metadata.get('source')])))
        prompt = f"""
        You’re an expert assistant synthesizing the final answer for the user.

        ❓ User wants a single, coherent response that includes **all relevant points** found above.

        🔑 Instructions:
        -**dont reply to greetings**
        - Craft a **complete answer** rather than a disjointed summary of bullet points.
        - Include **every piece of information** that directly answers any part of the original question.
        - Include the words which are there only in the provided context
        - Maintain a **natural, human tone** (as if you’re explaining to a friend).
        - **Do not** prefix with “Here’s a summary” or use list formatting.
        - **Do not** omit any critical detail that answers the user’s question.

        CONTEXT:
        ---
        {context}
        ---

        QUESTION: {query}

        ANSWER:
        """
        print("Generating answer...")
        response = self.llm.invoke(prompt)
        
        # --- THIS BLOCK WAS MISSING ---
        return {
            "answer": response.content,
            "pages": page_numbers,
            "sources": sources
        }
        # -----------------------------