
import os
import json
import requests
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

load_dotenv()
app = Flask(__name__)

print("🚀 STEP 0 ✅ Bot starting... loading vectorstore and model")

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
        print("❌ STEP 0.1 Token fetch failed:", e)
        return None

def send_lark_message(open_id, message):
    access_token = get_access_token()
    if not access_token:
        print("⚠️ STEP 7 ⚠️ No access token, message not sent.")
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
        print("✅ STEP 7 ✅ Message sent to Lark:", response.json())
    except Exception as e:
        print("❌ STEP 7 Message send failed:", e)

@app.route("/lark/events/org", methods=["POST"])
def handle_event():
    body = request.json
    print("✅ STEP 1 ✅ Received event:
", json.dumps(body, indent=2, ensure_ascii=False))

    if body.get("type") == "url_verification":
        print("✅ STEP 1.1 Challenge response")
        return jsonify({"challenge": body.get("challenge")})

    if body.get("header", {}).get("event_type") != "im.message.receive_v1":
        print("⏹ STEP 2 ❌ Not a message.receive_v1 event")
        return "OK"

    print("✅ STEP 2 ✅ Text event received")

    event = body.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {}).get("open_id", "")

    if sender_id == BOT_OPEN_ID:
        print("⏹ STEP 3 ❌ Message from self. Ignored.")
        return "OK"

    if message.get("message_type") != "text":
        print("⏹ STEP 3 ❌ Not a text message. Ignored.")
        return "OK"

    content = json.loads(message.get("content", "{}"))
    user_input = content.get("text", "").strip()
    print(f"✅ STEP 4 ✅ User asked: {user_input}")

    try:
        print("⏳ STEP 5 🔄 Calling qa_chain...")
        result = qa_chain({"question": user_input})
        print("✅ STEP 6 ✅ QA result:
", json.dumps(result, indent=2, ensure_ascii=False))

        answer = result.get("answer", "").strip()
        sources = result.get("sources", "").strip()

        if not answer or not sources or "I don't know" in answer:
            print("⚠️ STEP 6.1 Empty or no-source answer")
            answer = "Sorry, I can only answer questions related to Utopia Education. Please ask something specific about our platform."

    except Exception as e:
        print("❌ STEP 6.2 QA processing failed:")
        traceback.print_exc()
        answer = "Oops, I couldn't process your question. Please try again later."

    print("✅ STEP 6.3 Final answer:", answer)
    send_lark_message(sender_id, answer)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"🚀 STEP 0.9 Bot ready on port {port}")
    app.run(host="0.0.0.0", port=port)
