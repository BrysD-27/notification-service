from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta, timezone
from .models import EnqueuedNotification, NotifyReq
import uuid
from .scheduler import Scheduler

scheduler = Scheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):   
    # Ran at app startup
    await scheduler.start()
    yield # Code after 'yield' runs during shutdown

app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan) # Create FastAPI Application

def now_utc():
    """Return current UTC."""
    return datetime.now(timezone.utc)

def calculate_effective_time(scheduledTime, offset):
    """Calculate the effective time of a notification request."""
    base = scheduledTime or now_utc()
    return base + timedelta(minutes=offset or 0)

def _validate(channels, recipient):
    """Validate notification request: Channels and Recipients."""
    if not channels:
        raise HTTPException(400, "At least one channel is required.")
    
    # need at least one matching contact for selected channels
    missing_email = ("email" in channels and not recipient.email)
    missing_sms = ("sms" in channels and not recipient.sms)

    if missing_email and missing_sms:
        raise HTTPException(400, "At least one matching recipient contact is required.")

# Main notification endpoint
# 1. Validate request channels + recipients
# 2. Calculate effective time of notification
# 3. Validate effective time - return 400 if in the past
# 4. Build EnqueuedNotificaton model
# 5. (Future) Push to scheduler queue
# 6. Return successful response
@app.post("/api/notifications")
async def notify(req: NotifyReq):
    """Main notification POST endpoint."""
    _validate(req.channels, req.recipient)

    effective_time = calculate_effective_time(req.scheduledAt, req.offsetMinutes)
    if effective_time < now_utc() - timedelta(seconds=1):
        raise HTTPException(400, "effectiveSendAt is in the past.")
    notification = EnqueuedNotification(
        id=f"n_{uuid.uuid4().hex[:10]}",
        channels=req.channels,
        recipient=req.recipient,
        subject=req.subject,
        message=req.message,
        effectiveSendAt=effective_time,
        createdAt=now_utc()
    )

    await scheduler.enqueue(notification)
    return {
        "id": notification.id,
        "status": "queued",
        "channels": notification.channels,
        "effectiveSendAt": notification.effectiveSendAt.isoformat(),
        "createdAt": notification.createdAt.isoformat(),
    }

@app.get("/api/health")
async def health():
    """Return status of API service."""
    return {"status": "ok", "time": now_utc().isoformat()}
