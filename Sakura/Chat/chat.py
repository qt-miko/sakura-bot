import asyncio
import io
from typing import Optional, Dict

from PIL import Image
from google import genai

from Sakura import state
from Sakura.Chat.prompts import SAKURA_PROMPT
from Sakura.Core.config import AI_MODEL, GEMINI_API_KEY
from Sakura.Core.helpers import get_error, get_fallback, log_action
from Sakura.Core.logging import logger
from Sakura.Database.conversation import add_history, get_history


def init_client():
    """Initialize Gemini client for chat."""
    if not GEMINI_API_KEY:
        logger.warning("⚠️ No Gemini API key found, chat functionality will be disabled.")
        return

    logger.info("🫡 Initializing Gemini API key.")
    try:
        state.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ Chat client (Gemini) initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat client: {e}")

async def get_response(
    user_message: str,
    user_id: int,
    user_info: Dict[str, any] = None,
    image_bytes: Optional[bytes] = None,
) -> str:
    """Get response from Google Gemini API using a persistent chat session."""
    if user_info:
        log_action("DEBUG", f"🤖 Getting AI response for message: '{user_message[:50]}...'", user_info)

    if not state.gemini_client:
        if user_info:
            log_action("WARNING", "❌ Chat client not available, using fallback response", user_info)
        return get_fallback()

    try:
        model_to_use = AI_MODEL
        if user_info:
            log_action("INFO", f"🧠 Using model: {model_to_use}", user_info)

        # 1. Prepare history for the chat session
        history_raw = await get_history(user_id)
        chat_history = []
        # Add system prompt first
        chat_history.append({"role": "user", "parts": [SAKURA_PROMPT]})
        chat_history.append({"role": "model", "parts": ["Okay, I will follow these instructions and roleplay as Sakura."]})

        for msg in history_raw:
            role = "model" if msg["role"] == "assistant" else "user"
            chat_history.append({"role": role, "parts": [msg["content"]]})

        # The Gemini library's start_chat will manage conversation turns correctly.
        model = state.gemini_client.get_model(model_to_use)
        chat_session = model.start_chat(history=chat_history)

        # 2. Prepare the new message content
        parts = []
        if user_message:
            parts.append(user_message)

        history_message = user_message
        if image_bytes:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                parts.append(img)
                history_message = f"[Image Analysis]: {user_message}" if user_message else "[Image Analysis]"
            except Exception as e:
                log_action("ERROR", f"🖼️ Failed to process image: {e}", user_info)

        if not parts:
             if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
             return get_fallback()

        # 3. Send message and get response
        logger.debug("Sending message to Gemini chat session.")
        response = await chat_session.send_message_async(parts)
        logger.debug("Received response from Gemini chat session.")

        ai_response = response.text.strip() if response.text else get_fallback()

        # 4. Save to our database for future sessions
        if history_message or image_bytes:
            await add_history(user_id, history_message, is_user=True)
        await add_history(user_id, ai_response, is_user=False)

        if user_info:
            log_action("INFO", f"✅ AI response generated: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        import traceback
        full_error = traceback.format_exc()
        error_message = f"❌ AI API error: {e}\n{full_error}"
        if user_info:
            log_action("ERROR", error_message, user_info)
        else:
            logger.error(error_message)
        return get_error()
