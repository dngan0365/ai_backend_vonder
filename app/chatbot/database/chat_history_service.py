from typing import List, Dict, Optional
from datetime import datetime
import pytz
import warnings
from prisma.models import Chat, User, TitleChat
from app.db.prisma_client import prisma  # Import your prisma client

warnings.filterwarnings("ignore", category=ResourceWarning)


async def get_recent_chat_history(title_chat_id: str) -> List[dict]:
    """Fetch the 5 most recent chat messages by title chat ID"""
    if not title_chat_id:
        return []

    try:
        # Fetch only the 5 most recent chats, sorted descending
        chats = await prisma.chat.find_many(
            where={"titleChatId": title_chat_id},
            order={"createdAt": "desc"},
            take=4
        )

        # Return in chronological order
        return [chat.dict() for chat in reversed(chats)]
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return []

async def get_title_chat_with_messages(title_chat_id: str) -> Dict:
    """Fetch title chat with all its messages"""
    try:
        title_chat = await prisma.titlechat.find_unique(
            where={"id": title_chat_id},
            include={
                "chats": {"order_by": {"createdAt": "asc"}},
                "user": True
            }
        )
        if not title_chat:
            return {}
        
        return title_chat.dict()
    except Exception as e:
        print(f"Error fetching title chat: {e}")
        return {}


def format_chat_history(chats: List[Dict]) -> List[Dict]:
    """Format chat history for display"""
    if not chats:
        return []

    formatted_history = []
    for chat in chats:
        formatted_history.append({
            "role": "customer" if chat.get("role") == "USER" else "assistant",
            "content": chat.get("content", ""),
            "timestamp": chat.get("createdAt")
        })
    return formatted_history


async def get_user_info(user_id: str) -> dict:
    """Fetch user information by user ID"""
    try:
        user = await prisma.user.find_unique(where={"id": user_id})
        if not user:
            return {}
        
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "image": user.image,
            "role": user.role,
            "isOAuth": user.isOAuth,
            "createdAt": user.createdAt,
            "updatedAt": user.updatedAt
        }
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return {}


async def get_user_by_email(email: str) -> dict:
    """Fetch user information by email"""
    try:
        user = await prisma.user.find_unique(where={"email": email})
        if not user:
            return {}
        
        return user.dict()
    except Exception as e:
        print(f"Error fetching user by email: {e}")
        return {}


async def create_title_chat(user_id: str, title: str) -> Dict:
    """Create a new title chat for a user"""
    try:
        title_chat = await prisma.titlechat.create(
            data={
                "title": title,
                "userId": user_id
            }
        )
        return title_chat.dict()
    except Exception as e:
        print(f"Error creating title chat: {e}")
        return {}


async def create_chat_message(title_chat_id: str, role: str, content: str) -> Dict:
    """Create a new chat message"""
    try:
        # Validate role
        valid_roles = ["USER", "ASSISTANT"]  # Based on your ChatRole enum
        if role.upper() not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
        
        chat = await prisma.chat.create(
            data={
                "role": role.upper(),
                "content": content,
                "titleChatId": title_chat_id
            }
        )
        return chat.dict()
    except Exception as e:
        print(f"Error creating chat message: {e}")
        return {}


async def get_user_title_chats(user_id: str, limit: int = 10) -> List[Dict]:
    """Get recent title chats for a user"""
    try:
        title_chats = await prisma.titlechat.find_many(
            where={"userId": user_id},
            order_by={"updatedAt": "desc"},
            take=limit,
            include={"chats": {"take": 1, "order_by": {"createdAt": "desc"}}}
        )
        return [tc.dict() for tc in title_chats]
    except Exception as e:
        print(f"Error fetching user title chats: {e}")
        return []


async def update_title_chat(title_chat_id: str, title: str) -> bool:
    """Update title chat title"""
    try:
        await prisma.titlechat.update(
            where={"id": title_chat_id},
            data={"title": title}
        )
        return True
    except Exception as e:
        print(f"Error updating title chat: {e}")
        return False


async def delete_title_chat(title_chat_id: str, user_id: str) -> bool:
    """Delete a title chat (with user verification)"""
    try:
        await prisma.titlechat.delete(
            where={
                "id": title_chat_id,
                "userId": user_id  # Ensure user owns the chat
            }
        )
        return True
    except Exception as e:
        print(f"Error deleting title chat: {e}")
        return False


async def get_chat_statistics(user_id: str) -> Dict:
    """Get chat statistics for a user"""
    try:
        # Get total title chats
        total_conversations = await prisma.titlechat.count(
            where={"userId": user_id}
        )
        
        # Get total messages
        total_messages = await prisma.chat.count(
            where={"titleChat": {"userId": user_id}}
        )
        
        # Get messages by role
        user_messages = await prisma.chat.count(
            where={
                "titleChat": {"userId": user_id},
                "role": "USER"
            }
        )
        
        assistant_messages = await prisma.chat.count(
            where={
                "titleChat": {"userId": user_id},
                "role": "ASSISTANT"
            }
        )
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages
        }
    except Exception as e:
        print(f"Error getting chat statistics: {e}")
        return {}

