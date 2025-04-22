
from flask import Flask, request, render_template, redirect
import os
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename.endswith(".json"):
            filepath = os.path.join(UPLOAD_FOLDER, "knowledge_centre.json")
            file.save(filepath)

            # 替换主项目中的知识库
            shutil.copy(filepath, "knowledge_centre.json")

            # 自动触发向量库构建
            os.system("python build_vector_store.py")

            return "✅ 上传并更新知识库成功！"
        return "❌ 请上传 JSON 格式的文件。"

    return render_template("upload.html")

if __name__ == "__main__":
    app.run(port=8000)
