import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Khởi tạo Gemini Client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = "gemini-3.1-flash-lite"

CCCD_PROMPT = """
Bạn là AI chuyên đọc Căn cước công dân Việt Nam.

Trả về DUY NHẤT một JSON với các khóa:

{
    "isValidDocument": true,
    "fullName": "",
    "dob": "",
    "idCard": "",
    "issueDate": "",
    "issuePlace": "",
    "expiryDate": "",
    "address": "",
    "phone": null,
    "email": null
}

- isValidDocument: true nếu 2 ảnh thực sự là mặt trước/sau của một thẻ CCCD Việt Nam thật (có chữ và ảnh chân dung rõ ràng); false nếu ảnh trống, ảnh không liên quan, hoặc không đọc rõ được.
- Nếu isValidDocument = false, TẤT CẢ các khóa còn lại PHẢI là null. Không được tự bịa/đoán thông tin.
- issuePlace: CCCD mẫu cũ ghi dòng dài kiểu "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI". CCCD mẫu mới (từ 2021 trở đi) chỉ ghi ngắn gọn "BỘ CÔNG AN" — trường hợp này vẫn lấy đúng "Bộ Công An" làm giá trị, KHÔNG để null chỉ vì nó ngắn hơn mẫu cũ.
- Nếu không tìm thấy trường nào thì gán giá trị null.

Không giải thích.
Không thêm markdown.
Chỉ trả về JSON.
"""

HKD_PROMPT = """
Bạn là AI chuyên đọc Giấy chứng nhận đăng ký hộ kinh doanh (HKD) Việt Nam.

Trả về DUY NHẤT một JSON với các khóa:

{
    "isValidDocument": true,
    "businessName": "",
    "bizCode": "",
    "regNumber": "",
    "regDate": "",
    "bizIssuePlace": "",
    "businessAddress": "",
    "businessPhone": null,
    "industry": "",
    "industryCode": null,
    "capital": "",
    "capitalText": null
}

- isValidDocument: true nếu ảnh thực sự là Giấy chứng nhận đăng ký hộ kinh doanh Việt Nam thật, có tiêu đề "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" và "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH"; false nếu ảnh trống, ảnh không liên quan, ảnh khác loại giấy tờ, hoặc không đọc rõ được.
- Nếu isValidDocument = false, TẤT CẢ các khóa còn lại PHẢI là null. Không được tự bịa/đoán thông tin.

Giải thích các khóa còn lại:
- businessName: Tên hộ kinh doanh (mục 1)
- bizCode: Mã số hộ kinh doanh
- regNumber: Mã số đăng ký hộ kinh doanh
- regDate: Ngày đăng ký lần đầu (dd/mm/yyyy)
- bizIssuePlace: Nơi cấp — tên cơ quan cấp giấy chứng nhận, thường ghi ở góc trên bên trái ảnh (ví dụ "UBND QUẬN ... - PHÒNG TÀI CHÍNH - KẾ HOẠCH")
- businessAddress: Địa chỉ trụ sở hộ kinh doanh (mục 2)
- businessPhone: Số điện thoại
- industry: Tên ngành nghề kinh doanh chính (mục 3)
- industryCode: Mã ngành nghề chính
- capital: Vốn kinh doanh, ghi bằng số (mục 4)
- capitalText: Vốn kinh doanh ghi bằng chữ

Nếu không tìm thấy trường nào thì gán giá trị null.

Không giải thích.
Không thêm markdown.
Chỉ trả về JSON.
"""

COMPANY_PROMPT = """
Bạn là AI chuyên đọc Giấy chứng nhận đăng ký doanh nghiệp Việt Nam.

Trả về DUY NHẤT một JSON với các khóa:

{
    "isValidDocument": true,
    "companyName": "",
    "companyCode": "",
    "companyRegDate": "",
    "companyIssuePlace": "",
    "companyAddress": "",
    "companyPhone": null,
    "companyEmail": null,
    "charterCapital": "",
    "charterCapitalText": null,
    "shareParValue": null,
    "totalShares": null
}

- isValidDocument: true nếu ảnh thực sự là Giấy chứng nhận đăng ký doanh nghiệp Việt Nam thật, có tiêu đề "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" và "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP"; false nếu ảnh trống, ảnh không liên quan, ảnh khác loại giấy tờ, hoặc không đọc rõ được.
- Nếu isValidDocument = false, TẤT CẢ các khóa còn lại PHẢI là null. Không được tự bịa/đoán thông tin.

Giải thích các khóa còn lại:
- companyName: Tên công ty viết bằng tiếng Việt (mục 1)
- companyCode: Mã số doanh nghiệp
- companyRegDate: Ngày đăng ký lần đầu (dd/mm/yyyy)
- companyIssuePlace: Nơi cấp — tên cơ quan cấp giấy chứng nhận, thường ghi ở góc trên bên trái ảnh (ví dụ "SỞ TÀI CHÍNH THÀNH PHỐ ... - PHÒNG ĐĂNG KÝ KINH DOANH")
- companyAddress: Địa chỉ trụ sở chính (mục 2)
- companyPhone: Điện thoại
- companyEmail: Thư điện tử
- charterCapital: Vốn điều lệ, ghi bằng số (mục 3)
- charterCapitalText: Vốn điều lệ ghi bằng chữ
- shareParValue: Mệnh giá cổ phần (nếu có)
- totalShares: Tổng số cổ phần (nếu có)

Không cần trích xuất thông tin người đại diện theo pháp luật hay thành viên công ty — phần đó được nhập riêng.

Nếu không tìm thấy trường nào thì gán giá trị null.

Không giải thích.
Không thêm markdown.
Chỉ trả về JSON.
"""


def _call_gemini(prompt, parts):
    """Gọi Gemini với 1 prompt + danh sách ảnh, trả về dict đã parse JSON hoặc {"success": False, "message": ...}"""
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0
        )
        response = client.models.generate_content(
            model=MODEL,
            contents=[prompt] + parts,
            config=config
        )
        result = json.loads(response.text)

        # Lớp bảo vệ bằng code: nếu Gemini tự báo ảnh không hợp lệ,
        # ép TẤT CẢ field khác về null — không tin tưởng hoàn toàn vào việc
        # model "nhớ" đừng bịa dữ liệu, dù đã dặn trong prompt.
        is_valid = result.pop("isValidDocument", True)
        if not is_valid:
            result = {key: None for key in result}

        return result

    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "Gemini trả về JSON không hợp lệ"
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


def extract_cccd(front_bytes, front_mime, back_bytes, back_mime):
    front_part = types.Part.from_bytes(data=front_bytes, mime_type=front_mime)
    back_part = types.Part.from_bytes(data=back_bytes, mime_type=back_mime)
    return _call_gemini(CCCD_PROMPT, [
        "Ảnh mặt trước:", front_part,
        "Ảnh mặt sau:", back_part,
    ])


def extract_hkd(image_bytes, mime):
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    return _call_gemini(HKD_PROMPT, [part])


def extract_company(image_bytes, mime):
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    return _call_gemini(COMPANY_PROMPT, [part])
