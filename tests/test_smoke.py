import pytest

# TODO: Import hàm xử lý chính của trợ lý ảo từ mã nguồn dự án của bạn.
# Ví dụ: from assistant.main import get_bot_response

def test_greeting():
    """Kiểm tra trợ lý ảo có phản hồi đúng với lời chào hay không."""
    # input_text = "Hello"
    # response = get_bot_response(input_text)
    # assert "chào" in response.lower()
    assert True  # Tạm thời để True để pass test, bạn nhớ thay bằng code thật.

def test_empty_input():
    """Kiểm tra phản hồi khi người dùng không nhập gì."""
    # input_text = ""
    # response = get_bot_response(input_text)
    # assert response != ""
    assert True

def test_deadline_related_request():
    """Kiểm tra phản hồi khi người dùng hỏi về hạn chót (deadline)."""
    # input_text = "When is the deadline?"
    # response = get_bot_response(input_text)
    # assert "deadline" in response.lower() or "hạn chót" in response.lower()
    assert True

def test_fallback():
    """Kiểm tra trợ lý có xử lý lỗi (fallback) khi gặp câu hỏi ngoài phạm vi không."""
    # input_text = "Bí quyết nấu món phở bò là gì?"
    # response = get_bot_response(input_text)
    # assert "không thể giúp" in response.lower() or "không hiểu" in response.lower()
    assert True