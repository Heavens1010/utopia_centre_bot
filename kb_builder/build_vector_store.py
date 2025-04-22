import json
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document

load_dotenv()

embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

with open("knowledge_centre.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ✅ Use answer as the embedding content
docs = [Document(page_content=a, metadata={"question": q}) for q, a in data.items()]

db = Chroma.from_documents(docs, embedding, persist_directory="vector_store")
db.persist()
print("✅ Vector store built and saved.")