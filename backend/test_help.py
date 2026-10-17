import unittest
from main import AssistantBackend

class TestAssistantHelp(unittest.TestCase):
    def setUp(self):
        self.backend = AssistantBackend()

    # --- BỘ TEST CŨ CỦA BẠN (Giữ nguyên tiêu chí nghiệm thu ban đầu) ---
    def test_help(self):
        """
        Test that the backend correctly replies to 'help' with the list of capabilities.
        """
        response = self.backend.handle_message('help')
        
        # Acceptance criteria checks
        self.assertIn("Lists what the bot can do", response)
        self.assertIn("schedule view", response)
        self.assertIn("schedule add", response)
        self.assertIn("Here is what I can do for you", response)

    def test_help_case_insensitive(self):
        """
        Test that 'HELP' or '  help  ' variations also trigger the help command.
        """
        response_upper = self.backend.handle_message('HELP')
        response_spaced = self.backend.handle_message('  help  ')
        
        self.assertEqual(response_upper, response_spaced)
        self.assertIn("Lists what the bot can do", response_upper)


    # --- 2 BỘ TEST MỚI (Thêm vào theo yêu cầu tìm kiếm 'training') ---
    def test_training_keyword_finds_office(self):
        """Test mới 1: Từ khóa viết thường 'training' phải tìm thấy 'Training Office'"""
        response = self.backend.handle_message("training")
        self.assertIn("Training Office", response)
        self.assertIn("Found matching capabilities:", response)

    def test_training_office_exact_match(self):
        """Test mới 2: Nhập đầy đủ 'Training Office' vẫn tìm thấy chính xác"""
        response = self.backend.handle_message("Training Office")
        self.assertIn("Training Office", response)

if __name__ == '__main__':
    unittest.main()
