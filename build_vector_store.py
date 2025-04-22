import os
import json
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document

# Load environment variables
load_dotenv()

# Initialize OpenAI embedding model
embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Load Q&A pairs from JSON
with open("knowledge_centre.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Convert each Q&A pair to a LangChain Document
documents = [Document(page_content=answer, metadata={"question": question}) for question, answer in data.items()]

# Build vector store
db = Chroma.from_documents(documents, embedding, persist_directory="vector_store")
db.persist()

print("Vector store has been built and saved to 'vector_store/'.")
