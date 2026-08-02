import io
import zipfile


def build_zip(images: dict, docx_files: list[tuple[str, bytes]]) -> bytes:
    """Đóng gói ảnh (dict tên_file -> bytes) và (các) file Word vào 1 file zip trong bộ nhớ."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in images.items():
            zf.writestr(filename, content)
        for filename, content in docx_files:
            zf.writestr(filename, content)
    buffer.seek(0)
    return buffer.read()
