from bot.model.base_groq_model import GroqModelSettings


# Uses the same Meta Llama 3.1 8B Instruct model family as the local GGUF variant,
# but served via the Groq inference API (https://console.groq.com/docs/models).
class GroqLlama31EightSettings(GroqModelSettings):
    model_id = "llama-3.1-8b-instant"
    config_answer = {"temperature": 0.7, "stop": []}


class GroqLlama32OneSettings(GroqModelSettings):
    model_id = "llama-3.2-1b-preview"
    config_answer = {"temperature": 0.7, "stop": []}


class GroqLlama32ThreeSettings(GroqModelSettings):
    model_id = "llama-3.2-3b-preview"
    config_answer = {"temperature": 0.7, "stop": []}
