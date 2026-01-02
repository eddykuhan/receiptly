"""
Chat service for answering price comparison questions using GPT-4o-mini
"""
import json
import logging
from models.llm_client import LLMClient

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize LLM client
llm = LLMClient()

SYSTEM_PROMPT = """You are Cheapsy AI, a helpful Malaysian shopping assistant that helps users find the best prices for groceries.

You will be provided with price data from the gold layer (community-sourced receipt data) showing items, stores, and prices.

Your capabilities:
1. Find the cheapest store for a specific item
2. Compare prices across multiple stores
3. Optimize grocery lists by finding the best store for each item
4. Provide total cost estimates and savings calculations

Formatting guidelines:
- Use line breaks (\n) to separate different sections for better readability
- Format store listings with each store on a new line
- Add a blank line between the item name and store list
- Add a blank line before your recommendation
- Use emojis sparingly (💰 for cheapest, 📍 for location)

Content guidelines:
- Always use Malaysian Ringgit (RM) for prices
- Be concise and friendly
- If asked about an item not in the data, politely say you don't have price information for it
- Include store names and prices in your answers
- When optimizing lists, show per-item breakdown and total savings
- Reference how recent the data is

Example format:
You can find [ITEM NAME] at these stores:\n\n📍 Store 1: RM X.XX\n📍 Store 2: RM X.XX\n📍 Store 3: RM X.XX\n\n💰 The cheapest option is Store 1 at RM X.XX.\n\nPrices are from [date]. Happy shopping!

Don't use markdown formatting (no **, ##, or bullets).
"""


async def answer_price_question(question: str, price_data: dict) -> str:
    """
    Answer a price-related question using GPT-4o-mini
    
    Args:
        question: User's natural language question
        price_data: Dict with item names as keys and lists of store price data as values
                   e.g., {"milk": [{"store": "Store1", "avg_price": 5.50, ...}]}
    
    Returns:
        Natural language answer
    """
    logger.info(f"[answer_price_question] Processing question: {question}")
    logger.info(f"[answer_price_question] Price data type: {type(price_data)}")
    logger.info(f"[answer_price_question] Price data keys: {list(price_data.keys()) if isinstance(price_data, dict) else 'N/A'}")
    
    # Format price data for the prompt
    if not price_data:
        logger.warning("[answer_price_question] No price data available")
        context = "No price data available."
    else:
        total_items = len(price_data)
        total_stores = sum(len(stores) for stores in price_data.values())
        logger.info(f"[answer_price_question] Processing {total_items} items with {total_stores} total store entries")
        
        context = "Available price data:\n"
        for item_name, stores in price_data.items():
            logger.debug(f"[answer_price_question] Item '{item_name}' has {len(stores)} store entries")
            for store_data in stores[:20]:  # Limit stores per item
                context += f"- {item_name} at {store_data['store']}: RM {store_data['avg_price']:.2f} (last seen: {store_data['last_seen']}, {store_data['samples']} samples)\n"
    
    user_prompt = f"Question: {question}\n\n{context}"
    logger.debug(f"[answer_price_question] Context length: {len(context)} chars")
    logger.debug(f"[answer_price_question] Full prompt:\n{user_prompt}")
    
    try:
        logger.info("[answer_price_question] Calling LLM for answer generation")
        answer = await llm.chat(SYSTEM_PROMPT, user_prompt)
        logger.info(f"[answer_price_question] LLM response received (length: {len(answer)} chars)")
        logger.debug(f"[answer_price_question] LLM answer: {answer}")
        return answer
    
    except Exception as e:
        logger.error(f"[answer_price_question] Error generating answer: {str(e)}", exc_info=True)
        return f"Sorry, I encountered an error: {str(e)}"


async def extract_item_keywords(question: str) -> list:
    """
    Extract item names from a natural language question using GPT-4o-mini
    
    Args:
        question: User's question (e.g., "Where can I find cheap milk and bread?")
    
    Returns:
        List of item keywords (e.g., ["milk", "bread"])
    """
    logger.info(f"[extract_item_keywords] Extracting keywords from: {question}")
    
    system_prompt = """Extract product/item names from the user's shopping question. 
Return ONLY a JSON array of item names suitable for database search.

IMPORTANT RULES:
- Keep full product names together (e.g., "nescafe gold refill pack" stays as one item)
- Include brand names as part of the product (e.g., "milo", "nescafe gold")
- Do NOT break products into generic categories (e.g., "nescafe" should NOT become "coffee")
- Use lowercase for consistency
- Preserve the exact product description from the question

Examples:
"where can i buy milk" -> ["milk"]
"cheapest nescafe gold" -> ["nescafe gold"]
"nescafe gold refill pack" -> ["nescafe gold refill pack"]
"bread and eggs" -> ["bread", "eggs"]
"milo refill pack 1kg" -> ["milo refill pack"]

Return format: ["product name 1", "product name 2"]"""
    
    try:
        logger.info("[extract_item_keywords] Calling LLM for keyword extraction")
        content = await llm.chat(system_prompt, question)
        logger.debug(f"[extract_item_keywords] LLM raw response: {content}")
        
        # Parse JSON response
        items = json.loads(content)
        logger.info(f"[extract_item_keywords] Extracted {len(items) if isinstance(items, list) else 0} items: {items}")
        return items if isinstance(items, list) else []
    
    except Exception as e:
        logger.error(f"[extract_item_keywords] Error extracting keywords: {e}", exc_info=True)
        # Fallback: extract potential product names from the question
        # Remove common question words and extract nouns/product names
        question_lower = question.lower()
        stop_words = ['where', 'can', 'i', 'buy', 'find', 'get', 'cheapest', 'cheap', 'best', 'price', 'the', 'a', 'an', 'is', 'are', 'for', 'to']
        
        # Split and filter words
        words = question_lower.split()
        potential_items = [word.strip('?.,!') for word in words if word not in stop_words and len(word) > 2]
        
        # If we found potential items, return them joined as a phrase (for multi-word products like "nescafe gold")
        if potential_items:
            fallback_result = [' '.join(potential_items)]
            logger.warning(f"[extract_item_keywords] Using fallback extraction: {fallback_result}")
            return fallback_result
        
        logger.warning("[extract_item_keywords] No keywords found, returning empty list")
        return []
