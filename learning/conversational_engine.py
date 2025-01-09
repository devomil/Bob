import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class ConversationalEngine:
    def __init__(self):
        # Load pre-trained conversational model
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
        self.model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")
        self.chat_history = None  # Track conversation history

    def chat(self, input_text: str) -> str:
        """
        Generate a conversational response, including handling specific intents.

        Args:
            input_text (str): The user's input.

        Returns:
            str: The AI's response.
        """
        # Check for specific intents
        if "joke" in input_text.lower():
            return self.tell_a_joke()
        if "weather" in input_text.lower():
            return self.get_weather_response()

        # Regular conversational flow
        new_user_input_ids = self.tokenizer.encode(
            input_text + self.tokenizer.eos_token, return_tensors="pt"
        )

        bot_input_ids = (
            torch.cat([self.chat_history, new_user_input_ids], dim=-1)
            if self.chat_history is not None
            else new_user_input_ids
        )

        # Generate response
        self.chat_history = self.model.generate(
            bot_input_ids, max_length=1000, pad_token_id=self.tokenizer.eos_token_id
        )

        # Decode and return response
        return self.tokenizer.decode(
            self.chat_history[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True
        )

    def tell_a_joke(self) -> str:
        """
        Return a static joke (can be expanded later with an API).

        Returns:
            str: A simple joke.
        """
        return "Why don't scientists trust atoms? Because they make up everything!"

    def get_weather_response(self) -> str:
        """
        Return a placeholder response for weather-related queries.

        Returns:
            str: A weather response.
        """
        return "I can't check the weather yet, but I'm working on it!"
