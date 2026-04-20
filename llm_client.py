import os
from typing import Optional


class MockClient:
    """
    Offline stand-in for an LLM client.
    This lets the app run without an API key.
    """

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        # Very small, predictable behavior for demos.
        if "Return ONLY valid JSON" in system_prompt:
            # Purposely not JSON to force fallback unless students change behavior.
            return "I found some issues, but I'm not returning JSON right now."
        return "# MockClient: no rewrite available in offline mode.\n"


class GeminiClient:
    """
    Minimal Gemini API wrapper with added error resilience.

    Requirements:
    - google-generativeai installed
    - GEMINI_API_KEY set in environment (or loaded via python-dotenv)
    """

    def __init__(self, model_name: str = "gemini-2.5-flash", temperature: float = 0.2):
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "Missing GEMINI_API_KEY. Create a .env file and set GEMINI_API_KEY=..."
            )

        # Import here so heuristic mode doesn't require the dependency at import time.
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.genai = genai  # save so complete() can access it
        self.model = genai.GenerativeModel(model_name)
        self.temperature = float(temperature)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a single request to Gemini.

        UPDATED: Moved system_prompt to system_instruction parameter
        because Gemini does not support role: "system" in generate_content.
        If an error occurs, returns empty string to trigger heuristic fallback.
        """
        try:
            # Create a new model instance with the system prompt passed
            # as system_instruction — this is the correct way to send
            # a system prompt to the Gemini API.
            model = self.genai.GenerativeModel(
                self.model.model_name,
                system_instruction=system_prompt
            )
            
            # Send only the user prompt as the message content
            response = model.generate_content(
                user_prompt,
                generation_config={"temperature": self.temperature},
            )

            # Defensive check: response.text can be None if the response
            # was blocked by safety filters or returned empty
            return response.text or ""

        except Exception as e:
            # Returning empty string allows the agent to detect the failure
            # and switch to heuristic fallback logic
            return ""
