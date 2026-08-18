from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification

class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: UUID,
        message: str,
        type: str = "INFO"
    ) -> Notification:
        """
        Create a new notification for a user.
        """
        notification = Notification(
            user_id=user_id,
            message=message,
            type=type,
            is_read=False
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification
