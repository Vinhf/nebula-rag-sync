# app.py
import os
import json
from pathlib import Path
from langchain_core.documents import Document
from dotenv import load_dotenv
import streamlit as st
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import re


load_dotenv()


st.set_page_config(page_title="OptiBot", page_icon="🤖")
st.title("Support Assistant")
st.caption("Demo miễn phí – Dữ liệu được cập nhật tự động hàng ngày qua GitHub Actions")

def load_articles_with_metadata():
    docs = []
    url_map = {}  # map slug -> html_url (để dùng khi format citation)

    articles_dir = Path("articles")
    
    for md_path in articles_dir.glob("*.md"):
        slug = md_path.stem
        meta_path = articles_dir / f"{slug}.meta.json"
        
        article_url = "No URL found"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            article_url = meta.get("html_url") or meta.get("url") or "No URL found"
        
        url_map[slug] = article_url
        
        # Đọc nội dung .md
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Tạo Document chỉ với nội dung (không metadata)
        doc = Document(page_content=content)
        
        # Thêm slug vào metadata để map URL sau
        doc.metadata["slug"] = slug
        
        docs.append(doc)
    
    return docs, url_map

@st.cache_resource
def get_vectorstore():
    persist_dir = "./chroma_db_optisigns"

    # ✅ LUÔN load url_map (nhẹ, không tốn quota)
    _, url_map = load_articles_with_metadata()

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    if os.path.exists(persist_dir):
        # ✅ Chỉ load vectorstore
        vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings
        )
    else:
        docs, _ = load_articles_with_metadata()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=100
        )
        chunks = text_splitter.split_documents(docs)

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory="./chroma_db_optisigns"
        )

    return vectorstore.as_retriever(search_kwargs={"k": 4}), url_map

retriever, url_map = get_vectorstore()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0,
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
        slug = doc.metadata.get("slug", "")
        article_url = url_map.get(slug, "No URL found")
        
        main_content = content[:600] + "..."
        
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