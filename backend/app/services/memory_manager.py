import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


class MemoryManager:
    DEFAULT_WINDOW_SIZE = 6  # 3 user + 3 assistant turns

    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        initial_query: Optional[str] = None
    ) -> Conversation:
        if conversation_id:
            stmt = select(Conversation).where(
                Conversation.id == str(conversation_id),
                Conversation.workspace_id == str(workspace_id)
            )
            res = await db.execute(stmt)
            conv = res.scalars().first()
            if conv:
                return conv

        # Auto-create title from query
        title = "Research Session"
        if initial_query:
            clean_q = initial_query.strip().replace("\n", " ")
            title = clean_q[:45] + ("..." if len(clean_q) > 45 else "")

        new_conv = Conversation(
            id=str(uuid.uuid4()),
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            title=title,
            summary_memory=None,
        )
        db.add(new_conv)
        await db.commit()
        await db.refresh(new_conv)
        logger.info(f"Created new conversation session '{new_conv.id}' titled '{new_conv.title}'")
        return new_conv

    @staticmethod
    async def persist_user_message(
        db: AsyncSession,
        workspace_id: str,
        conversation_id: str,
        content: str
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            workspace_id=str(workspace_id),
            conversation_id=str(conversation_id),
            role=MessageRole.USER,
            content=content,
            citations=[],
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def persist_assistant_message(
        db: AsyncSession,
        workspace_id: str,
        conversation_id: str,
        content: str,
        citations: List[Dict[str, Any]]
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            workspace_id=str(workspace_id),
            conversation_id=str(conversation_id),
            role=MessageRole.ASSISTANT,
            content=content,
            citations=citations,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def get_window_and_summary(
        db: AsyncSession,
        conversation_id: str,
        window_size: int = DEFAULT_WINDOW_SIZE
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """
        Retrieves sliding window turns and maintains running summary memory.
        Returns: (recent_turns_dicts, running_summary_str)
        """
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == str(conversation_id))
        )
        res = await db.execute(stmt)
        conv = res.scalars().first()
        if not conv:
            return [], None

        messages = sorted(conv.messages or [], key=lambda m: m.created_at)
        total_messages = len(messages)

        # If within window size, all are raw turns
        if total_messages <= window_size:
            raw_turns = [
                {
                    "role": m.role.value if hasattr(m.role, "value") else str(m.role).lower(),
                    "text": m.content
                }
                for m in messages
            ]
            return raw_turns, conv.summary_memory

        # If exceeds window size, split into older turns and recent turns
        older_messages = messages[:-window_size]
        recent_messages = messages[-window_size:]

        # Check if older turns should be condensed into summary_memory
        existing_summary = conv.summary_memory or ""
        older_text_blocks = []
        for m in older_messages:
            role_name = m.role.value if hasattr(m.role, "value") else str(m.role).lower()
            older_text_blocks.append(f"{role_name.capitalize()}: {m.content[:500]}")
        older_history_str = "\n".join(older_text_blocks)

        try:
            summarizer_sys_instruction = (
                "You are an expert academic research assistant maintaining a concise running memory of an active research session.\n"
                "Synthesize the existing summary and earlier conversation turns into a high-density, factual summary (maximum 200 words).\n"
                "Focus on: (1) Main research questions asked, (2) Research papers referenced or compared, (3) Key technical conclusions and hardware/algorithmic choices."
            )
            user_prompt = (
                f"Existing Running Memory:\n{existing_summary or 'None (initial summary)'}\n\n"
                f"Earlier Turns to Compress:\n{older_history_str}\n\n"
                f"Generate the updated concise running memory:"
            )

            updated_summary = await LLMService.generate_response(
                system_instruction=summarizer_sys_instruction,
                user_prompt=user_prompt,
                temperature=0.2
            )

            if updated_summary and not updated_summary.startswith("Error"):
                conv.summary_memory = updated_summary.strip()
                await db.commit()
                await db.refresh(conv)
                logger.info(f"Updated conversation '{conv.id}' running memory successfully.")

        except Exception as exc:
            logger.error(f"Error updating running conversation summary: {exc}")

        raw_turns = [
            {
                "role": m.role.value if hasattr(m.role, "value") else str(m.role).lower(),
                "text": m.content
            }
            for m in recent_messages
        ]

        return raw_turns, conv.summary_memory
