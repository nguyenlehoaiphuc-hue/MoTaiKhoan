from docxtpl import DocxTemplate
import io
customer = {
    "fullName": "LÝ PHI HOÀNG",
    "dob": "08/03/2002",
    "idCard": "079202006521",
    "issueDate": "22/11/2021",
    "issuePlace": "Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "expiryDate": "08/03/2027",
    "address": "267 Tây Thạnh, Tây Thạnh, Tân Phú, Hồ Chí Minh",
    "phone": None,  # null trong JS tương đương None trong Python
}
def exportForm_MoTaiKhoan(data):
    doc = DocxTemplate("docx_templates/mau_mo_tai_khoan.docx")
    buffer = io.BytesIO()
    doc.render(data)
    doc.save(buffer)
    buffer.seek(0)   # đưa con trỏ đọc về đầu buffer, nếu không email sẽ đính kèm file rỗng
    return buffer
