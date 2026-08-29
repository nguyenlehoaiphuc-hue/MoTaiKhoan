from flask import Flask, render_template, request, jsonify, send_file
from gemini_service import extract_cccd, extract_hkd, extract_company
from supabase import create_client
import os
import json
import re
import io
import secrets
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font
from email_service import send_email
from docx_service import export_docx
from zip_service import build_zip

app = Flask(__name__)

supabase = create_client(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_key=os.getenv("SUPABASE_KEY")
)

CUSTOMER_FIELDS = [
    "workplace", "fullName", "dob", "idCard", "issueDate", "issuePlace",
    "expiryDate", "address", "phone", "customerEmail", "email",
]

# Chuyển field CCCD (fullName, dob, ...) sang field kế toán (accName, accDob, ...)
CCCD_TO_ACCOUNTANT_KEY = {
    "fullName": "accName",
    "dob": "accDob",
    "idCard": "accIdCard",
    "issueDate": "accIssueDate",
    "issuePlace": "accIssuePlace",
    "address": "accAddress",
}


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/mo-tai-khoan")
def index():
    return render_template("index.html")


@app.route("/scan_ocr", methods=["POST"])
def scan_ocr():
    mode = request.form.get("mode", "personal")

    if "image-front" not in request.files:
        return jsonify({"success": False, "message": "Thiếu ảnh mặt trước."}), 400
    if "image-back" not in request.files:
        return jsonify({"success": False, "message": "Thiếu ảnh mặt sau."}), 400
    if "image-phone-verify" not in request.files:
        return jsonify({"success": False, "message": "Thiếu ảnh định danh số điện thoại (TTTB)."}), 400

    front_image = request.files["image-front"]
    back_image = request.files["image-back"]

    result = extract_cccd(
        front_bytes=front_image.read(),
        front_mime=front_image.content_type,
        back_bytes=back_image.read(),
        back_mime=back_image.content_type
    )
    if result.get("success") is False:
        return jsonify(result)

    if mode == "business":
        if "image-hkd" not in request.files:
            return jsonify({"success": False, "message": "Thiếu ảnh Giấy chứng nhận HKD."}), 400
        hkd_image = request.files["image-hkd"]
        hkd_result = extract_hkd(hkd_image.read(), hkd_image.content_type)
        if hkd_result.get("success") is False:
            return jsonify(hkd_result)
        result.update(hkd_result)

    elif mode == "company":
        if "image-hkd" not in request.files:
            return jsonify({"success": False, "message": "Thiếu ảnh Giấy chứng nhận đăng ký DN."}), 400

        company_image = request.files["image-hkd"]
        company_result = extract_company(company_image.read(), company_image.content_type)
        if company_result.get("success") is False:
            return jsonify(company_result)
        result.update(company_result)

        # Ảnh CCCD kế toán không bắt buộc ở bước này — có route riêng
        # (/scan_accountant) tự chạy khi người dùng tải đủ 2 ảnh.

    return jsonify(result)


@app.route("/scan_accountant", methods=["POST"])
def scan_accountant():
    """Trích xuất riêng CCCD kế toán — gọi tự động khi đủ 2 ảnh, không cần bấm nút."""
    if "image-acc-front" not in request.files or "image-acc-back" not in request.files:
        return jsonify({"success": False, "message": "Thiếu ảnh CCCD kế toán."}), 400
    if "image-acc-phone-verify" not in request.files:
        return jsonify({"success": False, "message": "Thiếu ảnh định danh SĐT kế toán."}), 400

    acc_front = request.files["image-acc-front"]
    acc_back = request.files["image-acc-back"]
    acc_result = extract_cccd(
        front_bytes=acc_front.read(),
        front_mime=acc_front.content_type,
        back_bytes=acc_back.read(),
        back_mime=acc_back.content_type
    )
    if acc_result.get("success") is False:
        return jsonify(acc_result)

    result = {}
    for cccd_key, acc_key in CCCD_TO_ACCOUNTANT_KEY.items():
        result[acc_key] = acc_result.get(cccd_key)
    return jsonify(result)


def build_email_content(mode, data):
    """Trả về (subject, body_gdv, body_customer) tùy theo loại khách hàng."""
    if mode == "business":
        name = data.get("businessName") or data.get("fullName")
        subject = f"Mẫu mở tài khoản HKD {name}"
    elif mode == "company":
        name = data.get("companyName") or data.get("fullName")
        subject = f"Mẫu mở tài khoản công ty {name}"
    else:
        name = data.get("fullName")
        subject = f"Mẫu mở tài khoản KH {name}"

    workplace = data.get("workplace") or "(không có)"
    body_gdv = f"""Kính gửi: Anh/Chị,
KH {name} đã có form mở tài khoản.
Nơi làm việc: {workplace}
Vui lòng kiểm tra thông tin trước khi cho KH ký.
P/s: Đây là email tự động. Vui lòng không trả lời.
Trân trọng,
"""
    body_customer = """Kính gửi: Quý khách,
Form mở tài khoản của Quý khách đã được hoàn tất.
Vui lòng kiểm tra thông tin trước khi in.
P/s: Đây là email tự động. Vui lòng không trả lời.
Trân trọng,
"""
    return subject, body_gdv, body_customer, name


def safe_filename(name: str) -> str:
    """Loại bỏ ký tự không hợp lệ trong tên file (/, \\, :, v.v.)."""
    if not name:
        return "ho_so"
    return re.sub(r'[\\/:*?"<>|]', "", name).strip()


@app.route("/save_data", methods=["POST"])
def save_data():
    raw = request.form.to_dict()
    mode = raw.pop("mode", "personal")

    try:
        if mode == "personal":
            insert_data = {k: raw.get(k, "") for k in CUSTOMER_FIELDS}
            supabase.table("customer").insert(insert_data).execute()
        else:
            insert_data = dict(raw)
            insert_data["type"] = "hkd" if mode == "business" else "company"
            supabase.table("business").insert(insert_data).execute()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

    # Gửi email + đính kèm zip (ảnh + form mẫu) — lỗi ở đây không tính là lưu thất bại
    try:
        image_fields = [
            "image-front", "image-back", "image-phone-verify", "image-hkd",
            "image-acc-front", "image-acc-back", "image-acc-phone-verify",
        ]
        images = {}
        for field in image_fields:
            if field in request.files:
                f = request.files[field]
                images[f.filename or field] = f.read()

        docx_data = dict(raw)
        if docx_data.get("companyMembers"):
            try:
                docx_data["companyMembers"] = json.loads(docx_data["companyMembers"])
            except (json.JSONDecodeError, TypeError):
                docx_data["companyMembers"] = []
        else:
            docx_data["companyMembers"] = []
        docx_files = export_docx(mode, docx_data)
        zip_bytes = build_zip(images, docx_files)

        subject, body_gdv, body_customer, customer_name = build_email_content(mode, raw)
        mail_gdv = os.getenv("MAIL_GDV")
        zip_filename = f"{safe_filename(customer_name)}.zip"

        if raw.get("email"):
            send_email(raw["email"], mail_gdv, subject, body_customer, zip_bytes, zip_filename)
        else:
            send_email(mail_gdv, "", subject, body_gdv, zip_bytes, zip_filename)
    except Exception as e:
        print(e)

    return jsonify({"success": True})


NEED_TYPE_LABELS = {
    "vay": "Vay",
    "tiet-kiem": "Tiết kiệm",
    "khac": "Khác",
}


@app.route("/dang_ky_tu_van", methods=["POST"])
def dang_ky_tu_van():
    data = request.form.to_dict()
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    need_type = data.get("needType", "khac")
    message = data.get("message", "").strip()

    if not name or not phone:
        return jsonify({"success": False, "message": "Vui lòng nhập đầy đủ họ tên và số điện thoại."}), 400

    try:
        supabase.table("lead").insert({
            "name": name,
            "phone": phone,
            "needType": need_type,
            "message": message,
        }).execute()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

    try:
        need_label = NEED_TYPE_LABELS.get(need_type, "Khác")
        subject = f"[Đăng ký tư vấn] {name} - {need_label}"
        body = f"""Có khách hàng mới để lại thông tin tư vấn trên landing page:

Họ tên: {name}
Số điện thoại: {phone}
Nhu cầu: {need_label}
Lời nhắn: {message or "(không có)"}
"""
        mail_gdv = os.getenv("MAIL_GDV")
        send_email(mail_gdv, "", subject, body)
    except Exception as e:
        print(e)

    return jsonify({"success": True})


CUSTOMER_FIELD_LABELS = {
    "workplace": "Nơi làm việc",
    "fullName": "Họ và tên",
    "dob": "Ngày sinh",
    "idCard": "Số CCCD",
    "issueDate": "Ngày cấp",
    "issuePlace": "Nơi cấp",
    "expiryDate": "Ngày hết hạn",
    "address": "Địa chỉ",
    "phone": "Số điện thoại",
    "customerEmail": "Email khách hàng",
    "email": "Email nhận hồ sơ",
    "created_at": "Thời gian tạo",
}


def build_customer_excel():
    """Xuất toàn bộ bảng customer (KH cá nhân) ra file Excel trong bộ nhớ."""
    rows = supabase.table("customer").select("*").execute().data or []

    columns = list(CUSTOMER_FIELDS)
    if rows and "created_at" in rows[0]:
        columns.append("created_at")

    wb = Workbook()
    ws = wb.active
    ws.title = "Khach hang ca nhan"
    ws.append([CUSTOMER_FIELD_LABELS.get(c, c) for c in columns])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append([row.get(c, "") for c in columns])
    for col_cells in ws.columns:
        width = max((len(str(c.value or "")) for c in col_cells), default=10) + 2
        ws.column_dimensions[col_cells[0].column_letter].width = min(width, 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@app.route("/export", methods=["GET", "POST"])
def export_customers():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        admin_password = os.getenv("ADMIN_PASSWORD", "")
        if admin_password and secrets.compare_digest(password, admin_password):
            buffer = build_customer_excel()
            filename = f"khach_hang_ca_nhan_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            return send_file(
                buffer,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=filename,
            )
        error = "Mật khẩu không đúng."
    return render_template("export.html", error=error)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
