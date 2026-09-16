from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Literal
from datetime import datetime

Channel = Literal["email", "sms"]

class Recipient(BaseModel):
    email: Optional[EmailStr] = None
    sms: Optional[str] = Field(default=None, description="E.164 like +14055551234") # May change description / expected format later

class NotifyReq(BaseModel):
    recipient: Recipient
    channels: List[Channel]
    subject: Optional[str] = None
    message: str
    scheduledAt: Optional[datetime] = None
    offsetMinutes: Optional[int] = 0

class EnqueuedNotification(BaseModel):
    id: str
    channels: List[Channel]
    recipient: Recipient
    subject: Optional[str] = None
    message: str
    effectiveSendAt: datetime
    createdAt: datetime
