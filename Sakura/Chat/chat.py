import asyncio
import io
from typing import Optional, Dict

from PIL import Image
from google import genai

from Sakura import state
from Sakura.Chat.prompts import SAKURA_PROMPT
from Sakura.Core.config import AI_MODEL, GEMINI_API_KEY, OWNER_ID
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
    """Get response from Google Gemini API."""
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

        # Get and format conversation history
        history_raw = await get_history(user_id)
        history_formatted = []
        for msg in history_raw:
            # Gemini uses 'model' for assistant role
            role = "model" if msg["role"] == "assistant" else "user"
            history_formatted.append({"role": role, "parts": [msg["content"]]})

        # Prepare contents for Gemini API
        # System prompt is the first message in the history
        contents = [
            # User provides instructions
            {"role": "user", "parts": [SAKURA_PROMPT]},
            # Model acknowledges
            {"role": "model", "parts": ["Okay, I will follow these instructions and roleplay as Sakura."]}
        ]
        contents.extend(history_formatted)

        # Add current user message and image (if any)
        user_parts = []
        if user_message:
            user_parts.append(user_message)

        if image_bytes:
            try:
                # Gemini SDK can handle PIL images directly
                img = Image.open(io.BytesIO(image_bytes))
                user_parts.append(img)
                history_message = f"[Image Analysis]: {user_message}" if user_message else "[Image Analysis]"
            except Exception as e:
                log_action("ERROR", f"🖼️ Failed to process image: {e}", user_info)
                history_message = user_message
        else:
            history_message = user_message

        if not user_parts:
            if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
            return get_fallback()

        contents.append({"role": "user", "parts": user_parts})

        # Generate content using Gemini
        logger.debug("Sending request to Gemini API.")
        # Using client.aio.models.generate_content as per user example and memory
        response = await state.gemini_client.aio.models.generate_content(
            model=model_to_use,
            contents=contents,
        )
        logger.debug("Received response from Gemini API.")

        ai_response = response.text.strip() if response.text else get_fallback()

        # Save to conversation history
        if history_message:
            await add_history(user_id, history_message, is_user=True)
        await add_history(user_id, ai_response, is_user=False)

        if user_info:
            log_action("INFO", f"✅ AI response generated: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        # It's helpful to log the full error for debugging
        import traceback
        full_error = traceback.format_exc()
        error_message = f"❌ AI API error: {e}\n{full_error}"
        if user_info:
            log_action("ERROR", error_message, user_info)
        else:
            logger.error(error_message)
        return get_error()
