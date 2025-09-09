# 📄 Full-Stack Document Q&A with RAG and Gemini

This project is a complete web application that allows you to upload documents (PDF, TXT, Excel) and ask questions about their content. It uses the Retrieval-Augmented Generation (RAG) pattern with Google's Gemini Pro and Pinecone's vector database to provide accurate, context-aware answers.


*(**Note**: Replace the line above with a screenshot of your running application!)*

---

## ✨ Features

* **Multi-Format Document Upload**: Supports PDF, TXT, XLS, and XLSX files.
* **Intelligent PDF Processing**: Automatically extracts and understands text, clauses, and tables within PDFs.
* **Vector-Based Semantic Search**: Uses `text-embedding-004` and Pinecone to find the most relevant document chunks related to your question.
* **AI-Powered Answer Generation**: Leverages the `gemini-1.5-flash` model to synthesize answers based on the retrieved context.
* **Simple Web Interface**: A clean and user-friendly UI built with React to interact with the system.
* **Ready for Deployment**: Configured for easy hosting on platforms like Render.

---

## 🛠️ Tech Stack

| Backend                                                                                      | Frontend                                                       |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) | ![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB) |
| ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)           | ![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E) |
| ![LangChain](https://img.shields.io/badge/LangChain-008664?style=for-the-badge)               | `axios` for API calls                                          |
| ![Pinecone](https://img.shields.io/badge/pinecone-4A90E2?style=for-the-badge&logo=pinecone&logoColor=white) | `CSS` for styling                                              |
| ![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B9?style=for-the-badge&logo=google&logoColor=white) |                                                                |

---

## 🚀 Getting Started

Follow these instructions to get the project running on your local machine.

### Prerequisites

* **Python 3.8+**
* **Node.js v16+**
* **Git**
* **API Keys** for:
    * Google AI Studio
    * Pinecone

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git)
    cd rag-fullstack-app
    ```

2.  **Backend Setup:**
    ```bash
    # Navigate to the backend directory
    cd backend

    # Create and activate a virtual environment
    python -m venv venv
    .\venv\Scripts\Activate  # On Windows

    # Install Python dependencies
    pip install -r requirements.txt
    ```

3.  **Frontend Setup:**
    ```bash
    # Navigate to the frontend directory from the root
    cd frontend

    # Install Node.js dependencies
    npm install
    ```

### 🔑 Configuration

1.  In the `backend` directory, create a file named `.env`.
2.  Copy the contents of `.env.example` (if provided) or use the format below and add your secret keys:
    ```env
    GOOGLE_API_KEY="your_google_api_key_here"
    PINECONE_API_KEY="your_pinecone_api_key_here"
    ```

---

## 🏃‍♂️ Running the Application

You need to run both the backend and frontend servers in two separate terminals.

1.  **Start the Backend Server:**
    * Open a terminal in the `backend` directory.
    * Make sure your virtual environment is activated.
    * Run the server:
        ```bash
        uvicorn main:app --reload
        ```
    * The backend will be running at `http://localhost:8000`.

2.  **Start the Frontend Server:**
    * Open a **new** terminal in the `frontend` directory.
    * Run the React app:
        ```bash
        npm start
        ```
    * The application will open automatically in your browser at `http://localhost:3000`.

---

## Usage

1.  Navigate to `http://localhost:3000` in your browser.
2.  Click **Choose File** to select a document.
3.  Click **Upload & Index**. Wait for the success message.
4.  Type your question into the text area.
5.  Click **Ask** to receive an answer from the AI.