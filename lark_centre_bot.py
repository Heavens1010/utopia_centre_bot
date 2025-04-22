
import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Setup vector database and QA chain
embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vectorstore = Chroma(persist_directory="vector_store", embedding_function=embedding)
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY")),
    chain_type="stuff",
    retriever=vectorstore.as_retriever()
)

def get_access_token():
    try:
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
    except Exception as e:
        print("❌ Failed to fetch Lark token:", e)
        return None

def send_lark_message(open_id, message):
    access_token = get_access_token()
    if not access_token:
        print("⚠️ No access token. Message not sent.")
        return

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
    try:
        response = requests.post(url, headers=headers, json=payload)
        print("📤 Lark message send result:", response.json())
    except Exception as e:
        print("❌ Failed to send Lark message:", e)

@app.route("/lark/events/org", methods=["POST"])
def lark_event_handler():
    print("🧵 Full raw request received")
    print(json.dumps(request.json, indent=2, ensure_ascii=False))
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

        try:
            answer = qa_chain.run(user_question)
        except Exception as e:
            print("❌ QA chain failed:", e)
            answer = "Oops, I ran into an error. Please try again later."

        print("🟢 Answer sent:", answer)
        send_lark_message(open_id, answer)

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
