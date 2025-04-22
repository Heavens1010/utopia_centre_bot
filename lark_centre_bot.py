
import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

load_dotenv()

app = Flask(__name__)

# Load vector store and build RetrievalQA with sources
embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vectorstore = Chroma(persist_directory="vector_store", embedding_function=embedding)
retriever = vectorstore.as_retriever()

qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
    llm=ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"), temperature=0),
    retriever=retriever,
    return_source_documents=True
)

BOT_OPEN_ID = os.getenv("BOT_OPEN_ID", "")

def get_access_token():
    try:
        url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        payload = {
            "app_id": os.getenv("LARK_APP_ID"),
            "app_secret": os.getenv("LARK_APP_SECRET")
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json().get("tenant_access_token")
    except Exception as e:
        print("❌ Token fetch failed:", e)
        return None

def send_lark_message(open_id, message):
    access_token = get_access_token()
    if not access_token:
        print("⚠️ No access token, message not sent.")
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
        print("📤 Message sent to Lark:", response.json())
    except Exception as e:
        print("❌ Message send failed:", e)

@app.route("/lark/events/org", methods=["POST"])
def handle_event():
    body = request.json
    print("📥 Incoming event:", json.dumps(body, indent=2, ensure_ascii=False))

    if body.get("type") == "url_verification":
        return jsonify({"challenge": body.get("challenge")})

    if body.get("header", {}).get("event_type") == "im.message.receive_v1":
        event = body.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {}).get("open_id", "")

        if sender_id == BOT_OPEN_ID:
            print("⏹ Ignored self message.")
            return "OK"

        if message.get("message_type") != "text":
            print("⏹ Ignored non-text message.")
            return "OK"

        content = json.loads(message.get("content", "{}"))
        user_question = content.get("text", "").strip()
        print(f"💬 Question from {sender_id}: {user_question}")

        try:
            result = qa_chain({"question": user_question})
            answer = result.get("answer", "").strip()
            sources = result.get("sources", "").strip()

            # If answer is empty or from no source, assume hallucination
            if not answer or not sources or "I don't know" in answer:
                answer = "Sorry, I can only answer questions related to Utopia Education. Please ask something specific about our platform."

        except Exception as e:
            print("❌ QA processing failed:", e)
            answer = "Oops, I couldn't process your question. Please try again later."

        print("🟢 Final answer:", answer)
        send_lark_message(sender_id, answer)

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
