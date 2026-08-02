from docxtpl import DocxTemplate
import io

# mode -> danh sách (tên file khi gửi mail, đường dẫn template)
TEMPLATES_BY_MODE = {
    "personal": [
        ("form_mo_tai_khoan.docx", "docx_templates/canhan_mau_mo_tai_khoan.docx"),
    ],
    "business": [
        ("form_mo_tai_khoan.docx", "docx_templates/hkd_mau_mo_tai_khoan.docx"),
    ],
    "company": [
        ("form_mo_tai_khoan.docx", "docx_templates/cong_ty_mau_mo_tai_khoan.docx"),
        ("form_efast.docx", "docx_templates/efast_cty.docx"),
    ],
}


def export_docx(mode: str, data: dict) -> list[tuple[str, bytes]]:
    """Điền dữ liệu vào (các) template Word tương ứng với mode.
    Trả về danh sách (tên_file, bytes) — bỏ qua template nào lỗi hoặc chưa có file."""
    results = []
    for out_name, template_path in TEMPLATES_BY_MODE.get(mode, []):
        try:
            doc = DocxTemplate(template_path)
            buffer = io.BytesIO()
            doc.render(data)
            doc.save(buffer)
            buffer.seek(0)
            results.append((out_name, buffer.read()))
        except Exception:
            continue
    return results
