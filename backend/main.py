class AssistantBackend:
    def __init__(self):
        # Định nghĩa các tính năng/lịch trình của trợ lý cá nhân
        self.capabilities = [
            "Help: Show all available commands and capabilities.",
            "Scheduling: Manage your daily calendar and appointments.",
            "Training Office: View and manage professional development sessions."
        ]

    def handle_message(self, message: str) -> str:
        """
        Xử lý tin nhắn đầu vào từ người dùng.
        - Trả về danh sách tính năng nếu tin nhắn là 'help'.
        - Tìm kiếm tính năng phù hợp nếu tin nhắn chứa từ khóa.
        """
        if not message:
            return "Please say something."
            
        clean_msg = message.strip().lower()

        # Xử lý lệnh 'help' cơ bản
        if clean_msg == 'help':
            return "Here is what I can do:\n" + "\n".join([f"- {cap}" for cap in self.capabilities])

        # Tìm kiếm các tính năng chứa từ khóa (Yêu cầu mới)
        matched_capabilities = [
            cap for cap in self.capabilities 
            if clean_msg in cap.lower()
        ]

        if matched_capabilities:
            return "Found matching capabilities:\n" + "\n".join([f"- {cap}" for cap in matched_capabilities])

        return "I'm sorry, I don't understand that command. Type 'help' to see what I can do."
