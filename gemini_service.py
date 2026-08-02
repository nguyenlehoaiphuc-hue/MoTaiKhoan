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

PROMPT = """
Bạn là AI chuyên đọc Căn cước công dân Việt Nam.

Dưới đây gồm:
- Ảnh 1: Mặt trước CCCD
- Ảnh 2: Mặt sau CCCD

Hãy kết hợp thông tin từ cả hai ảnh.

Trả về DUY NHẤT một JSON với các khóa:

{
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

Nếu không tìm thấy trường nào thì gán giá trị null.

Không giải thích.
Không thêm markdown.
Chỉ trả về JSON.
"""


def extract_cccd(front_bytes, front_mime, back_bytes, back_mime):

    try:

        front_part = types.Part.from_bytes(
            data=front_bytes,
            mime_type=front_mime
        )

        back_part = types.Part.from_bytes(
            data=back_bytes,
            mime_type=back_mime
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                PROMPT,
                "Ảnh mặt trước:",
                front_part,
                "Ảnh mặt sau:",
                back_part
            ],
            config=config
        )

        return json.loads(response.text)

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