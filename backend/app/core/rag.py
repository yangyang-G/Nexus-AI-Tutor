import os
from typing import List, Optional
import shutil
import re
from fastapi import UploadFile

# Add debug print to check if module is loading
print("Loading app.core.rag module...")

try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.documents import Document
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError as e:
    print(f"Error importing dependencies in rag.py: {e}")
    raise

# Initialize Embeddings
# Using BAAI/bge-m3 for better multilingual support (English & Chinese)
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
try:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
except Exception as e:
    print(f"Error initializing embeddings: {e}")
    embeddings = None

# Initialize Vector Store
vector_store = None
FAISS_INDEX_PATH = "faiss_index"

def get_vector_store():
    global vector_store
    if vector_store is None:
        if os.path.exists(FAISS_INDEX_PATH):
            try:
                if embeddings:
                    vector_store = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
                    print("Vector store loaded successfully.")
            except Exception as e:
                print(f"Error loading vector store: {e}")
                vector_store = None
    return vector_store

def save_vector_store():
    global vector_store
    if vector_store:
        vector_store.save_local(FAISS_INDEX_PATH)

def clear_vector_store():
    global vector_store
    vector_store = None
    if os.path.exists(FAISS_INDEX_PATH):
        shutil.rmtree(FAISS_INDEX_PATH)
        print("Vector store cleared.")

def clean_text(text: str) -> str:
    """
    Remove abnormal symbols from text.
    Keeps:
    - Chinese characters (\u4e00-\u9fa5)
    - English letters (a-zA-Z)
    - Numbers (0-9)
    - Basic punctuation and whitespace
    """
    # Regex pattern:
    # \u4e00-\u9fa5 : Chinese characters
    # a-zA-Z : English letters
    # 0-9 : Numbers
    # \s : Whitespace (spaces, tabs, newlines)
    # \.,!?:;'"\(\)\[\]\{\} : Basic punctuation (add more if needed)
    # The caret ^ inside [] means "not matches"
    # So we replace anything that is NOT in this set with empty string
    
    # Expanded punctuation list to cover common English and Chinese punctuation
    # Chinese punctuation: ，。！？；：“”‘’（）【】《》、
    # English punctuation: ,.!?:;""''()[]{}<>/-_
    
    pattern = r"[^\u4e00-\u9fa5a-zA-Z0-9\s,.\!?:;\"'()\[\]\{\}<>/\-_\uff0c\uff01\uff1f\uff1b\uff1a\u201c\u201d\u2018\u2019\uff08\uff09\u3010\u3011\u300a\u300b\u3001\u3002]"
    cleaned_text = re.sub(pattern, "", text)
    
    # Remove multiple spaces/newlines to cleanup
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text

async def process_files(files: List[UploadFile], mode: str = "append") -> str:
    """
    Process uploaded files:
    1. Extract text
    2. Clean text (remove abnormal symbols)
    3. Split into chunks (with metadata) -> "Store in DB" (FAISS docstore)
    4. Vectorize text -> "Store in Vector DB" (FAISS index)
    5. Support Append/Refactor modes
    """
    global vector_store
    
    if not embeddings:
        return "Error: Embedding model not initialized."

    # If mode is refactor, clear existing store
    if mode == "refactor":
        clear_vector_store()

    total_chunks = 0
    processed_files = []

    for file in files:
        # Save temp file
        temp_filename = f"temp_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            documents = []
            if file.filename.endswith(".pdf"):
                try:
                    loader = PyPDFLoader(temp_filename)
                    documents = loader.load()
                except Exception as e:
                    print(f"Error loading PDF {file.filename}: {e}")
                    continue
            else:
                # Assume text based
                try:
                    with open(temp_filename, "r", encoding="utf-8") as f:
                        text = f.read()
                    documents = [Document(page_content=text, metadata={"source": file.filename})]
                except Exception as e:
                    print(f"Error reading text file {file.filename}: {e}")
                    continue

            if not documents:
                continue

            # Clean content of each document
            for doc in documents:
                doc.page_content = clean_text(doc.page_content)

            # Filter out empty documents after cleaning
            documents = [doc for doc in documents if doc.page_content.strip()]
            
            if not documents:
                print(f"File {file.filename} is empty after cleaning.")
                continue

            # Text Splitting
            # Chunk Size: 300 - 500 (avg 400), Overlap: 50
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=400, 
                chunk_overlap=50
            )
            splits = text_splitter.split_documents(documents)
            
            if not splits:
                continue

            # Add to Vector Store
            # FAISS.from_documents handles both:
            # 1. Storing text/metadata (DB)
            # 2. Calculating embeddings & storing vectors (Vector DB)
            if vector_store is None:
                vector_store = FAISS.from_documents(splits, embeddings)
            else:
                vector_store.add_documents(splits)
            
            total_chunks += len(splits)
            processed_files.append(file.filename)
            print(f"Processed {file.filename}: {len(splits)} chunks.")
            
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
    
    if total_chunks > 0:
        save_vector_store()
        return f"Processed {len(processed_files)} files ({total_chunks} chunks). Mode: {mode}"
    else:
        return "No content processed."

async def chat_with_rag(question: str, model: str = "deepseek"):
    global vector_store
    
    # Initialize LLM
    try:
        if model == "chatgpt":
            llm = ChatOpenAI(
                model="gpt-5.2", 
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.7
            )
        elif model == "gemini":
            llm = ChatGoogleGenerativeAI(
                model="gemini-3.0-flash",
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0.7
            )
        else: # deepseek or default
            llm = ChatOpenAI(
                model="deepseek-chat", 
                openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
                openai_api_base="https://api.deepseek.com",
                temperature=0.7
            )
    except Exception as e:
        return f"Error initializing LLM ({model}): {e}"

    # Ensure vector store is loaded
    get_vector_store()

    if vector_store is None:
        # Fallback if no docs
        print("Vector store empty, asking LLM directly.")
        return await llm.ainvoke(question)

    # Retriever
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # Prompt
    template = """Answer the question based only on the following context:
{context}

Question: {question}
"""
    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs):
        return "\n\n".join([d.page_content for d in docs])

    # RAG Chain
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return await chain.ainvoke(question)
