import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

load_dotenv()

app = Flask(__name__)

embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vectorstore = Chroma(persist_directory="vector_store", embedding_function=embedding)
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY")),
    chain_type="stuff",
    retriever=vectorstore.as_retriever()
)

def get_access_token():
    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    payload = {
        "app_id": os.getenv("LARK_APP_ID"),
        "app_secret": os.getenv("LARK_APP_SECRET")
    }
    response = requests.post(url, headers=headers, json=payload)
    res_data = response.json()
    print("🛑 Token response:", res_data)
    return res_data["tenant_access_token"]

def send_lark_message(open_id, message):
    access_token = get_access_token()
    url = "https://open.larksuite.com/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": message})
    }
    response = requests.post(url, headers=headers, json=payload)
    print("📤 Lark message send result:", response.json())

@app.route("/lark/events/org", methods=["POST"])
def lark_event_handler():
    body = request.json
    if body.get("type") == "url_verification":
        return jsonify({"challenge": body["challenge"]})

    if body.get("header", {}).get("event_type") == "im.message.receive_v1":
        event = body["event"]
        message = event["message"]
        sender = event["sender"]
        open_id = sender["sender_id"]["open_id"]
        content = json.loads(message["content"])
        user_question = content.get("text", "")
        print("🟡 User message:", user_question)

        results = vectorstore.similarity_search(user_question, k=3)
        if results:
            print("🔍 Matched question:", results[0].metadata.get("question", "N/A"))
            print("✅ Answer returned:", results[0].page_content)
            answer = results[0].page_content
        else:
            print("🔴 No vector match found")
    else:
        answer = "Sorry, I don't know the answer to that yet."

        print("🟢 Answer sent:", answer)
        send_lark_message(open_id, answer)

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
