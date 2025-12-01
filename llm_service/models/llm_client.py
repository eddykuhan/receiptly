from openai import AsyncOpenAI
from groq import AsyncGroq
from config import get_settings

class LLMClient:
    def __init__(self):
        settings = get_settings()
        if settings.USE_GROQ:
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            self.model = "llama-3.1-8b-instant"
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.MODEL_NAME

    async def chat(self, system_prompt, user_prompt):
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content.strip()
