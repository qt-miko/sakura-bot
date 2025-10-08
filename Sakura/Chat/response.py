from typing import Optional, Dict

from Sakura.Chat.chat import get_response as _get_chat_response
from Sakura.Core.helpers import get_error, log_action


async def get_response(
    user_message: str,
    user_info: Dict[str, any],
    user_id: int,
    image_bytes: Optional[bytes] = None,
) -> str:
    """
    Gets a response from the AI.
    This is a wrapper that handles exceptions and ensures a fallback response.
    History management is handled by the core _get_chat_response function.
    """
    try:
        response = await _get_chat_response(
            user_message, user_id, user_info, image_bytes
        )
        return response or get_error()

    except Exception as e:
        log_action("ERROR", f"❌ Error getting AI response: {e}", user_info)
        return get_error()