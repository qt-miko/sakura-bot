from Sakura.Core.config import CHAT_LENGTH
from Sakura.Core.logging import logger
from Sakura import state

async def add_history(user_id: int, message: str, is_user: bool = True):
    """Add message to user's conversation history (in-memory)."""
    role = "user" if is_user else "assistant"
    new_message = {"role": role, "content": message}

    if user_id not in state.conversation_history:
        state.conversation_history[user_id] = []

    history = state.conversation_history[user_id]
    history.append(new_message)

    if len(history) > CHAT_LENGTH:
        state.conversation_history[user_id] = history[-CHAT_LENGTH:]


async def update_history(user_id: int, user_message: str, ai_response: str):
    """Add both user message and AI response to history."""
    await add_history(user_id, user_message, is_user=True)
    await add_history(user_id, ai_response, is_user=False)
    logger.debug(f"📜 Updated conversation history for user {user_id}")


async def get_history(user_id: int) -> list:
    """Get conversation history as a list of dicts from memory."""
    return state.conversation_history.get(user_id, [])

async def get_context(user_id: int) -> str:
    """Get formatted conversation context for the user."""
    history = await get_history(user_id)
    if not history:
        return ""
    context_lines = [f"User: {msg['content']}" if msg["role"] == "user" else f"Sakura: {msg['content']}" for msg in history]
    return "\n".join(context_lines)