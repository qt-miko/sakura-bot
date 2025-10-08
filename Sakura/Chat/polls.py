import random
from typing import Dict
from pyrogram import Client
from pyrogram.types import Message
from Sakura.Core.helpers import log_action
from Sakura.Modules.effects import animate_reaction
from Sakura.Modules.reactions import CONTEXTUAL_REACTIONS
from Sakura.Modules.typing import send_typing
from Sakura.Chat.chat import get_response

POLL_ANALYSIS_TRIGGERS = [
    "poll", "polls", "question", "questions", "query", "queries", "quiz", "quiz question",
    "answer", "answers", "reply", "replies", "solution", "solutions",
    "correct", "wrong", "galat", "sahi", "right", "incorrect", "true", "false",
    "option", "options", "choice", "choices", "selection", "selections",
    "batao", "jawab", "kya hai", "kya hai ye", "ye kya hai", "isme kya hai",
    "ismein kya hai", "sawal", "sawal ka jawab", "jawab do", "btao mujhe",
    "tell me", "what is", "which", "which one", "pick one", "choose one", "kaunsa sahi",
    "kaunsa galat", "kaunsa option", "kaunsa choice"
]

async def reply_poll(client: Client, message: Message, user_message: str, user_info: dict) -> bool:
    """Check if user is asking to analyze a previously sent poll and handle it"""
    message_lower = user_message.lower()
    contains_poll_request = any(trigger in message_lower for trigger in POLL_ANALYSIS_TRIGGERS)

    if not contains_poll_request:
        return False

    log_action("DEBUG", "🔍 Detected potential poll analysis request", user_info)

    if message.reply_to_message and message.reply_to_message.poll:
        log_action("INFO", "🔍 User asking about replied poll", user_info)

        try:
            emoji_to_react = random.choice(CONTEXTUAL_REACTIONS["confused"])
            await animate_reaction(
                chat_id=message.chat.id,
                message_id=message.id,
                emoji=emoji_to_react
            )
            await animate_reaction(
                chat_id=message.chat.id,
                message_id=message.reply_to_message.id,
                emoji=emoji_to_react
            )
            log_action("INFO", f"🤔 Sent analysis reaction '{emoji_to_react}' for replied poll", user_info)
        except Exception as e:
            log_action("WARNING", f"⚠️ Could not send analysis reaction for replied poll: {e}", user_info)

        await send_typing(client, message.chat.id, user_info)

        try:
            poll = message.reply_to_message.poll
            poll_question = poll.question
            poll_options = [option.text for option in poll.options]

            response = await analyze_poll(
                poll_question, poll_options, user_info, user_info["user_id"]
            )
            await message.reply_text(response)
            log_action("INFO", "✅ Referenced poll analyzed successfully", user_info)
            return True
        except Exception as e:
            log_action("ERROR", f"❌ Error analyzing referenced poll: {e}", user_info)
            error_response = "Poll analyze nahi kar paa rahi 😔"
            await message.reply_text(error_response)
            return True
    return False

async def analyze_poll(poll_question: str, poll_options: list, user_info: Dict[str, any], user_id: int) -> str:
    """Analyzes a poll by formatting a prompt for the unified chat AI."""
    if user_info:
        log_action("DEBUG", f"📊 Analyzing poll: '{poll_question[:50]}...'", user_info)

    try:
        options_text = "\n".join([f"{i + 1}. {option}" for i, option in enumerate(poll_options)])

        # Create a concise prompt for the core get_response function
        # The system prompt and history are handled by get_response
        poll_prompt_message = f"""Please analyze the following poll and tell me the most likely correct answer and a brief reason why.

Poll Question: "{poll_question}"

Options:
{options_text}
"""

        response = await get_response(
            user_message=poll_prompt_message,
            user_id=user_id,
            user_info=user_info,
        )

        if response:
            log_action("INFO", "✅ Poll analysis completed", user_info)
            return response
        else:
            return "Poll analyze nahi kar paa rahi 😕"

    except Exception as e:
        if user_info:
            log_action("ERROR", f"❌ Poll analysis error: {e}", user_info)
        return "Poll analyze nahi kar paa rahi 😕"