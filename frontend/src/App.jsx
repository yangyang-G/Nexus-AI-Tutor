import React, { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am Nexus AI Tutor. Upload a PDF/TXT document to start learning.' }
  ])
  const [input, setInput] = useState('')
  const [files, setFiles] = useState([])
  const [uploadMode, setUploadMode] = useState('append')
  const [selectedModel, setSelectedModel] = useState('deepseek')
  const [isModelOpen, setIsModelOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const dropdownRef = useRef(null)

  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsModelOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [dropdownRef])

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files))
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    formData.append('mode', uploadMode)
    
    setUploading(true)
    setUploadStatus('Uploading...')

    try {
      const response = await axios.post('http://localhost:8000/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setUploadStatus(response.data.message)
      setFiles([]) // Clear selection after upload
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `✅ **Upload Complete!**\n\n${response.data.message}` 
      }])
    } catch (error) {
      console.error('Error:', error)
      setUploadStatus('Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() && files.length === 0) return

    const newMessages = [...messages, { role: 'user', content: input }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    const formData = new FormData()
    formData.append('question', input)
    formData.append('model', selectedModel)
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i])
    }

    try {
      const response = await axios.post('http://localhost:8000/api/chat', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      setMessages([...newMessages, { 
        role: 'assistant', 
        content: response.data.answer 
      }])
    } catch (error) {
      console.error('Error:', error)
      setMessages([...newMessages, { 
        role: 'assistant', 
        content: 'Sorry, something went wrong. Please ensure the backend is running.' 
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const modelOptions = [
    { value: "deepseek", label: "DeepSeek V3" },
    { value: "chatgpt", label: "ChatGPT (GPT-5.2)" },
    { value: "gemini", label: "Gemini 3.0 Flash" }
  ]

  const selectedLabel = modelOptions.find(opt => opt.value === selectedModel)?.label

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          Nexus AI Tutor
        </div>

        <div className="upload-card">
          <p className="card-title">Document Upload</p>
          <p className="card-desc">
            Upload PDF or TXT files to chat with your documents.
          </p>
          
          <div className="file-upload-container">
            <input 
              id="file-upload"
              type="file" 
              multiple 
              onChange={handleFileChange} 
              accept=".pdf,.txt" 
              className="file-input-hidden"
            />
            <label htmlFor="file-upload" className="file-upload-label">
              <div className="icon-wrapper">
                📂
              </div>
              <span className="upload-text">
                {files.length > 0 
                  ? `${files.length} file(s) selected` 
                  : 'Click to upload PDF / TXT'}
              </span>
            </label>
          </div>
          
          <div className="mode-select">
            <label className="radio-label">
              <input 
                type="radio" 
                value="append" 
                checked={uploadMode === 'append'} 
                onChange={(e) => setUploadMode(e.target.value)} 
              />
              Append
            </label>
            <label className="radio-label">
              <input 
                type="radio" 
                value="refactor" 
                checked={uploadMode === 'refactor'} 
                onChange={(e) => setUploadMode(e.target.value)} 
              />
              Reset & New
            </label>
          </div>

          <button 
            className="btn-primary" 
            onClick={handleUpload} 
            disabled={files.length === 0 || uploading}
            style={{ marginBottom: '20px' }}
          >
            {uploading ? 'Processing...' : 'Upload Files'}
          </button>
          
          {uploadStatus && <div className="status-msg">{uploadStatus}</div>}

          <div className="model-section" style={{ marginTop: '20px' }}>
            <p className="card-title">Model Selection</p>
            <div className="custom-select-container" ref={dropdownRef}>
              <div 
                className={`custom-select-trigger ${isModelOpen ? 'open' : ''}`} 
                onClick={() => setIsModelOpen(!isModelOpen)}
              >
                <span>{selectedLabel}</span>
                <span className="arrow">▼</span>
              </div>
              {isModelOpen && (
                <div className="custom-select-options">
                  {modelOptions.map(option => (
                    <div 
                      key={option.value}
                      className={`custom-select-option ${selectedModel === option.value ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedModel(option.value)
                        setIsModelOpen(false)
                      }}
                    >
                      {option.label}
                      {selectedModel === option.value && <span className="check">✓</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-area">
        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role === 'user' ? 'user-message' : 'ai-message'}`}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          ))}
          {loading && (
            <div className="message ai-message">
              <span className="typing-indicator">Thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <input 
            type="text" 
            className="chat-input"
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask a question about your documents..." 
            disabled={loading}
          />
          <button 
            className="btn-primary" 
            style={{width: 'auto', padding: '0 24px'}}
            onClick={handleSend} 
            disabled={loading}
          >
            Send
          </button>
        </div>
      </main>
    </div>
  )
}

export default App
