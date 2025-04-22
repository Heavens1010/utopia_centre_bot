
import os
import json
import requests
import traceback
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

load_dotenv()
app = Flask(__name__)
print("🚀 STEP 0 ✅ Bot starting...")

embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vectorstore = Chroma(persist_directory="vector_store", embedding_function=embedding)
retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
    llm=ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0,
        request_timeout=10  # timeout in seconds
    ),
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
    print("✅ STEP 1 ✅ Received event:")
    print("Final JSON body:", json.dumps(body, indent=2, ensure_ascii=False))

    if body.get("type") == "url_verification":
        return jsonify({"challenge": body.get("challenge")})

    if body.get("header", {}).get("event_type") != "im.message.receive_v1":
        return "OK"

    event = body.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {}).get("open_id", "")

    if sender_id == BOT_OPEN_ID:
        return "OK"

    if message.get("message_type") != "text":
        return "OK"

    content = json.loads(message.get("content", "{}"))
    user_input = content.get("text", "").strip()
    print(f"✅ STEP 4 ✅ User asked: {user_input}")

    try:
        print("⏳ STEP 5 🔄 Calling qa_chain()...")
        start = time.time()
        result = qa_chain({"question": user_input})
        duration = time.time() - start
        print(f"✅ STEP 6 ✅ QA result (took {duration:.2f}s):", result)

        answer = result.get("answer", "").strip()
        sources = result.get("sources", "").strip()

        if not answer or not sources or "I don't know" in answer:
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
    app.run(host="0.0.0.0", port=port)
