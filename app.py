# app.py
import os
import json
from pathlib import Path
from xml.dom.minidom import Document
from dotenv import load_dotenv
import streamlit as st
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import re


load_dotenv()


st.set_page_config(page_title="OptiBot", page_icon="🤖")
st.title("OptiBot – Support Assistant")
st.caption("Demo miễn phí – Dữ liệu được cập nhật tự động hàng ngày qua GitHub Actions")

def load_articles_with_metadata():
    docs = []
    articles_dir = Path("articles")
    
    for md_path in articles_dir.glob("*.md"):
        slug = md_path.stem
        meta_path = articles_dir / f"{slug}.meta.json"
        
        if not meta_path.exists():
            continue  # bỏ qua nếu không có meta
        
        # Đọc meta
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        
        article_url = meta.get("html_url") or meta.get("url") or "No URL found"
        
        # Đọc nội dung .md
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Tạo document với metadata chứa URL thật
        doc = Document(
            page_content=content,
            metadata={
                "source": md_path.name,
                "html_url": article_url,
                "title": meta.get("title", slug.replace("-", " ").title())
            }
        )
        docs.append(doc)
    
    return docs
# Load documents
@st.cache_resource
def get_vectorstore():
    
    docs = load_articles_with_metadata() [:5]

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)

    embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
    )

    vectorstore = Chroma.from_documents(
    chunks,
    embeddings,
    persist_directory="./chroma_db_optisigns"
    )
    return vectorstore.as_retriever(search_kwargs={"k": 4})

retriever = get_vectorstore()

llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=0.3,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

prompt_template = """
You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points.
• Cite up to 3 "Article URL:" lines per reply.

Context:
{context}

Question: {question}

Answer:
"""

prompt = ChatPromptTemplate.from_template(prompt_template)




def format_docs(docs):
    formatted = []
    for doc in docs:
        content = doc.page_content
        article_url = doc.metadata.get("html_url", "No URL found")
        
        # Cắt nội dung chính (bỏ front-matter nếu cần)
        main_content = content[:600] + "..."  # đơn giản, hoặc tinh chỉnh thêm
        
        formatted.append(f"Article URL: {article_url}\n{main_content}")
    
    return "\n\n".join(formatted)

chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Hỏi tôi về OptiSigns..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        response = chain.invoke(prompt)
        st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})