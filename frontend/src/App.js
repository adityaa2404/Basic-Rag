import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // We will create this file for styling

function App() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  //const API_URL = "http://localhost:8000"; // Your FastAPI backend URL
  const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setUploadStatus('');
    setResponse(null);
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a file first!");
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    setUploadStatus('Uploading and processing...');
    setIsLoading(true);

    try {
      const res = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setUploadStatus(`✅ ${res.data.filename} uploaded successfully (${res.data.message})`);
    } catch (error) {
      setUploadStatus(`❌ Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!query) {
      alert("Please enter a question!");
      return;
    }
    
    setIsLoading(true);
    setResponse(null);

    try {
      const res = await axios.post(`${API_URL}/query`, { query });
      setResponse(res.data);
    } catch (error) {
      setResponse({ answer: `Error: ${error.response?.data?.detail || error.message}`, pages: [], sources: [] });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>📄 RAG Document Q&A</h1>
        <p>Upload a document and ask it anything!</p>
      </header>
      
      <div className="container">
        <div className="card upload-card">
          <h2>1. Upload a Document</h2>
          <p>Supports PDF, TXT, XLS, XLSX</p>
          <input type="file" onChange={handleFileChange} accept=".pdf,.txt,.xls,.xlsx" />
          <button onClick={handleUpload} disabled={isLoading || !file}>
            {isLoading && uploadStatus.includes('Uploading') ? 'Processing...' : 'Upload & Index'}
          </button>
          {uploadStatus && <p className="status-message">{uploadStatus}</p>}
        </div>

        <div className="card query-card">
          <h2>2. Ask a Question</h2>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., What are the main benefits covered?"
            rows="3"
          />
          <button onClick={handleQuery} disabled={isLoading}>
            {isLoading && !uploadStatus.includes('Uploading') ? 'Thinking...' : 'Ask'}
          </button>
          
          {response && (
            <div className="response-area">
              <h3>Answer:</h3>
              <p>{response.answer}</p>
              {response.sources && response.sources.length > 0 && (
                <div className="metadata">
                  <p><strong>Source:</strong> {response.sources.join(', ')}</p>
                  {response.pages && response.pages.length > 0 && (
                     <p><strong>Pages:</strong> {response.pages.join(', ')}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;