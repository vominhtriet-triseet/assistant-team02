# main.py
# Backend component for Personal Assistant Bot

class AssistantBackend:
    def __init__(self):
        self.capabilities = [
            "help - Lists what the bot can do",
            "schedule view - View your daily schedule",
            "schedule add - Add a new appointment or task",
            "schedule remove - Delete an existing task"
        ]

    def handle_message(self, message: str) -> str:
        """
        Processes incoming messages and returns the appropriate response.
        """
        if not message:
            return "I didn't catch that. Type 'help' to see what I can do."
            
        normalized_message = message.strip().lower()
        
        if normalized_message == 'help':
            return self.get_help_message()
            
        return "Command not recognized. Type 'help' to see all available commands."

    def get_help_message(self) -> str:
        """
        Returns a formatted string listing all bot capabilities.
        """
        prefix = "Here is what I can do for you:\n"
        return prefix + "\n".join(f"- {cap}" for cap in self.capabilities)

if __name__ == "__main__":
    backend = AssistantBackend()
    print("Personal Assistant Backend initialized. Type 'help' to test:")
    user_input = input("> ")
    print(backend.handle_message(user_input))
