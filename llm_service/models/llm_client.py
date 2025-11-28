import os
from openai import AsyncOpenAI
from groq import AsyncGroq

USE_GROQ = os.getenv("USE_GROQ", "true").lower() == "true"

class LLMClient:
    def __init__(self):
        if USE_GROQ:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
            self.model = "llama-3.1-8b-instant"
        else:
            self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = os.getenv("MODEL_NAME", "gpt-4o-mini")

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
