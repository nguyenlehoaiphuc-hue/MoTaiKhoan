from flask import Flask, render_template, request, jsonify
from gemini_service import extract_cccd
from supabase import create_client
import os
import json
from email_service import send_email
from docx_service import exportForm_MoTaiKhoan

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scan_ocr", methods=["POST"])
def scan_ocr():

    if "image-front" not in request.files:
        return jsonify({
            "success": False,
            "message": "Thiếu ảnh mặt trước."
        }), 400

    if "image-back" not in request.files:
        return jsonify({
            "success": False,
            "message": "Thiếu ảnh mặt sau."
        }), 400

    front_image = request.files["image-front"]
    back_image = request.files["image-back"]

    result = extract_cccd(
        front_bytes=front_image.read(),
        front_mime=front_image.content_type,
        back_bytes=back_image.read(),
        back_mime=back_image.content_type
    )

    return jsonify(result)

supabase = create_client(
    supabase_url = os.getenv("SUPABASE_URL"),
    supabase_key = os.getenv("SUPABASE_KEY")
)
@app.route("/save_data", methods=["POST"])
def save_data():
    data = request.form.to_dict()
    try:
        supabase.table("customer").insert(data).execute()
        try: 
            mailGDV = os.getenv("MAIL_GDV")
            name_customer = data["fullName"]
            subject = f"Mẫu mở tài khoản KH {name_customer}"
            attachment_bytes = exportForm_MoTaiKhoan(data).read()
            if(data["email"] == ""):
                reciever = mailGDV
                body = f"""Kính gửi: Anh/Chị,
                KH {name_customer} đã có form mở tài khoản. 
                Vui lòng kiểm tra thông tin trước khi cho KH ký.
                P/s: Đây là email tự động. Vui lòng không trả lời.
                Trân trọng, 
                """
                
                send_email(reciever,"",subject,body, attachment_bytes)
            else:
                reciever = data["email"]
                cc = mailGDV
                body ="""Kính gửi: Quý khách,
                Form mở tài khoản của Quý khách đã được hoàn tất.
                Vui lòng kiểm tra thông tin trước khi in.
                P/s: Đây là email tự động. Vui lòng không trả lời.
                Trân trọng, 
                """
                send_email(reciever,cc,subject,body,attachment_bytes)
        except Exception as e:
            print(e)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })
if __name__ == "__main__":
    app.run(debug=True)


