from openai import AsyncOpenAI
from groq import AsyncGroq
from config import get_settings

class LLMClient:
    def __init__(self):
        settings = get_settings()
        if settings.USE_GROQ:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY is not set but USE_GROQ=true")
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            self.model = "llama-3.1-8b-instant"
        else:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set")
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.MODEL_NAME

    async def chat(self, system_prompt, user_prompt):
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM API Error: {type(e).__name__}: {str(e)}")
            raise

    async def embed(self, text, model="text-embedding-3-small"):
        try:
            # We use text-embedding-3-small for 1536 dims (same as configured in DB)
            response = await self.client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding API Error: {str(e)}")
            return None
