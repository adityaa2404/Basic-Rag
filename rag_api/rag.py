# rag_api/rag.py
import os
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pymupdf
from langchain.docstore.document import Document
# We are removing concurrent.futures as it's no longer needed for this simplified approach
import re
from typing import List, Dict, Any
import pandas as pd

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

if not GOOGLE_API_KEY:
    raise ValueError("🔴 GOOGLE_API_KEY not found. Please set it in your .env file.")
if not PINECONE_API_KEY:
    raise ValueError("🔴 PINECONE_API_KEY not found. Please set it in your .env file.")


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

    def _flatten_table(self, table_data):
        if not table_data or len(table_data) < 2: return []
        headers = [str(h).strip() for h in table_data[0]]
        flattened_rows = []
        for row in table_data[1:]:
            subject = str(row[0]).strip()
            if not subject: continue
            for i, cell in enumerate(row[1:]):
                cell_text = str(cell).strip()
                header = headers[i + 1]
                if cell_text and header:
                    sentence = f"For the benefit '{subject}', the value under '{header}' is '{cell_text}'."
                    flattened_rows.append(sentence)
        return flattened_rows

    def _group_clauses(self, text: str) -> list[str]:
        pattern = r'(\n\d+\)\s.*?\(Code\s-\w+\)|\n[a-z]\.\s)'
        parts = re.split(pattern, text)
        grouped_clauses = []
        if parts[0] and parts[0].strip(): grouped_clauses.append(parts[0].strip())
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                heading = parts[i].strip()
                content = parts[i+1].strip()
                grouped_clauses.append(f"{heading}\n{content}")
            else:
                grouped_clauses.append(parts[i].strip())
        return [clause for clause in grouped_clauses if clause]

    def _process_pdf_page(self, page_data):
        page_num, pdf_path = page_data
        standardized_path = pdf_path.replace(os.sep, '/')
        # NOTE: The PyMuPDF doc object is opened and closed within this function
        doc = pymupdf.open(pdf_path)
        page = doc.load_page(page_num)
        processed_units = []
        tables = page.find_tables()
        for table in tables:
            table_data = table.extract()
            flattened_sentences = self._flatten_table(table_data)
            for sentence in flattened_sentences:
                processed_units.append(Document(page_content=sentence, metadata={'page': page_num + 1, 'type': 'table', 'source': standardized_path}))
        text = page.get_text()
        for table in tables:
            text = text.replace(page.get_text(clip=table.bbox), "")
        clauses = self._group_clauses(text)
        for clause in clauses:
            processed_units.append(Document(page_content=clause, metadata={'page': page_num + 1, 'type': 'clause', 'source': standardized_path}))
        doc.close()
        return processed_units

    def load_document(self, file_path: str) -> List[Document]:
        standardized_path = file_path.replace(os.sep, '/')
        ext = os.path.splitext(file_path)[1].lower()
        documents = []
        
        ### MODIFIED SECTION ###
        # Replaced parallel processing with a simple, robust loop
        if ext == ".pdf":
            try:
                doc = pymupdf.open(file_path)
                # Process pages sequentially in a simple loop
                for i in range(len(doc)):
                    result = self._process_pdf_page((i, file_path))
                    documents.extend(result)
                doc.close()
            except Exception as e:
                print(f"Error loading PDF file {file_path}: {e}")
        ### END MODIFIED SECTION ###

        elif ext == ".txt":
            try:
                loader = TextLoader(file_path)
                documents = loader.load()
                for doc in documents: doc.metadata['source'] = standardized_path
            except Exception as e:
                print(f"Error loading Text file {file_path}: {e}")
        elif ext in [".xls", ".xlsx"]:
            try:
                df = pd.read_excel(file_path)
                text_content = df.to_string()
                documents.append(Document(page_content=text_content, metadata={'source': standardized_path, 'type': 'excel'}))
            except Exception as e:
                print(f"Error loading Excel file {file_path}: {e}")
        
        print(f"📄 Loaded {len(documents)} initial document sections from {os.path.basename(file_path)}")
        return documents

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        if not documents: return []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = text_splitter.split_documents(documents)
        print(f"🧩 Created {len(chunks)} chunks from the document.")
        return chunks

    def index_documents(self, documents: List[Document]):
        print(f"🌲 Attempting to index {len(documents)} chunks in Pinecone...")
        if not documents: 
            print("⚠️ No chunks to index. Skipping Pinecone operation.")
            return
        self.vector_store.add_documents(documents)
        print("✅ Indexing call to Pinecone completed.")

    def ask_question(self, query: str) -> Dict[str, Any]:
        if not self.vector_store:
            return {"answer": "RAG system not initialized.", "pages": [], "sources": []}
        retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        retrieved_docs = retriever.invoke(query)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        page_numbers = sorted(list(set([doc.metadata.get('page') for doc in retrieved_docs if doc.metadata.get('page')])))
        sources = sorted(list(set([os.path.basename(doc.metadata.get('source', '')) for doc in retrieved_docs if doc.metadata.get('source')])))
        prompt = f"""
        CONTEXT:
        ---
        {context}
        ---
        QUESTION: {query}
        
        ANSWER (Based only on the context provided):
        """
        response = self.llm.invoke(prompt)
        return {"answer": response.content, "pages": page_numbers, "sources": sources}
        
    def delete_document(self, source_file_path: str):
        standardized_path = source_file_path.replace(os.sep, '/')
        print(f"Attempting to delete document with standardized path: {standardized_path}")
        try:
            index = self.pc.Index(self.pinecone_index_name)
            delete_response = index.delete(
                filter={"source": {"$eq": standardized_path}}
            )
            print(f"Pinecone delete response: {delete_response}")
            print(f"✅ Successfully deleted chunks for document: {source_file_path}")
        except Exception as e:
            print(f"🔴 Error deleting document chunks from Pinecone: {e}")
            raise e