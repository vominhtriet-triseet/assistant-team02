# test_backend.py
import unittest
from main import AssistantBackend

class TestAssistantHelp(unittest.TestCase):
    def setUp(self):
        self.backend = AssistantBackend()

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

if __name__ == '__main__':
    unittest.main()
