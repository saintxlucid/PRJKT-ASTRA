"""
Conversation service.

Manages conversation lifecycle and message persistence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from astra.infrastructure.storage.database import Conversation, DatabaseManager, Message
from astra.utils.errors import DatabaseQueryError, NotFoundError
from astra.utils.logging import LoggerMixin


class ConversationService(LoggerMixin):
    """
    Service for managing conversations and messages.

    Handles CRUD operations for conversations and their messages.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize conversation service.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    def create_conversation(self, title: Optional[str] = None) -> str:
        """
        Create a new conversation.

        Args:
            title: Optional conversation title

        Returns:
            conversation_id: UUID of the new conversation

        Raises:
            DatabaseQueryError: If creation fails
        """
        session = self.db.get_session()
        try:
            conversation_id = str(uuid4())
            conversation = Conversation(
                conversation_id=conversation_id,
                title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            )
            session.add(conversation)
            session.commit()

            self.logger.info(
                "conversation_created",
                conversation_id=conversation_id,
                title=conversation.title,
            )

            return conversation_id

        except Exception as e:
            session.rollback()
            self.logger.error("create_conversation_failed", error=str(e))
            raise DatabaseQueryError(f"Failed to create conversation: {e}") from e
        finally:
            session.close()

    def get_conversation(self, conversation_id: str) -> dict:
        """
        Get a conversation by ID.

        Args:
            conversation_id: UUID of the conversation

        Returns:
            Dictionary with conversation data

        Raises:
            NotFoundError: If conversation not found
            DatabaseQueryError: If query fails
        """
        session = self.db.get_session()
        try:
            conversation = (
                session.query(Conversation)
                .filter(Conversation.conversation_id == conversation_id)
                .first()
            )

            if not conversation:
                raise NotFoundError(
                    f"Conversation not found: {conversation_id}",
                    code="CONVERSATION_NOT_FOUND",
                )

            return {
                "conversation_id": conversation.conversation_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "message_count": len(conversation.messages),
            }

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                "get_conversation_failed",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise DatabaseQueryError(f"Failed to get conversation: {e}") from e
        finally:
            session.close()

    def list_conversations(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        List all conversations.

        Args:
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip

        Returns:
            List of conversation dictionaries

        Raises:
            DatabaseQueryError: If query fails
        """
        session = self.db.get_session()
        try:
            conversations = (
                session.query(Conversation)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            result = []
            for conv in conversations:
                result.append(
                    {
                        "conversation_id": conv.conversation_id,
                        "title": conv.title,
                        "created_at": conv.created_at.isoformat(),
                        "updated_at": conv.updated_at.isoformat(),
                        "message_count": len(conv.messages),
                    }
                )

            self.logger.debug("conversations_listed", count=len(result))
            return result

        except Exception as e:
            self.logger.error("list_conversations_failed", error=str(e))
            raise DatabaseQueryError(f"Failed to list conversations: {e}") from e
        finally:
            session.close()

    def delete_conversation(self, conversation_id: str):
        """
        Delete a conversation and all its messages.

        Args:
            conversation_id: UUID of the conversation

        Raises:
            NotFoundError: If conversation not found
            DatabaseQueryError: If deletion fails
        """
        session = self.db.get_session()
        try:
            conversation = (
                session.query(Conversation)
                .filter(Conversation.conversation_id == conversation_id)
                .first()
            )

            if not conversation:
                raise NotFoundError(
                    f"Conversation not found: {conversation_id}",
                    code="CONVERSATION_NOT_FOUND",
                )

            session.delete(conversation)
            session.commit()

            self.logger.info("conversation_deleted", conversation_id=conversation_id)

        except NotFoundError:
            raise
        except Exception as e:
            session.rollback()
            self.logger.error(
                "delete_conversation_failed",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise DatabaseQueryError(f"Failed to delete conversation: {e}") from e
        finally:
            session.close()

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> int:
        """
        Add a message to a conversation.

        Args:
            conversation_id: UUID of the conversation
            role: Message role (system, user, assistant)
            content: Message content

        Returns:
            message_id: Database ID of the new message

        Raises:
            NotFoundError: If conversation not found
            DatabaseQueryError: If insertion fails
        """
        session = self.db.get_session()
        try:
            # Check if conversation exists
            conversation = (
                session.query(Conversation)
                .filter(Conversation.conversation_id == conversation_id)
                .first()
            )

            if not conversation:
                raise NotFoundError(
                    f"Conversation not found: {conversation_id}",
                    code="CONVERSATION_NOT_FOUND",
                )

            # Add message
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
            )
            session.add(message)

            # Update conversation timestamp
            conversation.updated_at = datetime.utcnow()

            session.commit()

            self.logger.debug(
                "message_added",
                conversation_id=conversation_id,
                message_id=message.id,
                role=role,
            )

            return message.id

        except NotFoundError:
            raise
        except Exception as e:
            session.rollback()
            self.logger.error(
                "add_message_failed",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise DatabaseQueryError(f"Failed to add message: {e}") from e
        finally:
            session.close()

    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """
        Get messages from a conversation.

        Args:
            conversation_id: UUID of the conversation
            limit: Maximum number of messages to return (most recent)

        Returns:
            List of message dictionaries

        Raises:
            NotFoundError: If conversation not found
            DatabaseQueryError: If query fails
        """
        session = self.db.get_session()
        try:
            # Check if conversation exists
            conversation = (
                session.query(Conversation)
                .filter(Conversation.conversation_id == conversation_id)
                .first()
            )

            if not conversation:
                raise NotFoundError(
                    f"Conversation not found: {conversation_id}",
                    code="CONVERSATION_NOT_FOUND",
                )

            # Get messages
            query = session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.asc())

            if limit:
                # Get most recent N messages
                query = query.order_by(Message.created_at.desc()).limit(limit)
                messages = query.all()
                messages.reverse()  # Return in chronological order
            else:
                messages = query.all()

            result = []
            for msg in messages:
                result.append(
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                    }
                )

            self.logger.debug(
                "messages_retrieved",
                conversation_id=conversation_id,
                count=len(result),
            )

            return result

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                "get_messages_failed",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise DatabaseQueryError(f"Failed to get messages: {e}") from e
        finally:
            session.close()
