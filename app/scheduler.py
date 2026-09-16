import asyncio
from datetime import datetime, timezone
import heapq
from typing import Tuple
from .models import EnqueuedNotification
from .delivery import deliver

# UTC Helper method
def now_utc():
    return datetime.now(timezone.utc)

class Scheduler:
    """Background worker: schedules and delivers notifications at their effective time."""

    # init of service worker
    def __init__(self):
        self._schedule_queue: list[Tuple[float, str, EnqueuedNotification]] = []
        self._queue_event = asyncio.Condition()
        self._task: asyncio.Task | None = None
        self._is_active = False

    async def start(self):
        """Start the schedule queue service."""
        self._is_active = True
        self._task = asyncio.create_task(self._run())

    async def enqueue(self, notification: EnqueuedNotification):
        """Push a notification to queue."""
        when_ts = notification.effectiveSendAt.timestamp() # Grab timestamp of effective time of notification
        async with self._queue_event:
            heapq.heappush(self._schedule_queue, (when_ts, notification.id, notification)) # push notification tuple to queue
            self._queue_event.notify_all() # Wake queue event to see if new item is earlier than previous head

    async def _run(self):
        """Continuously monitor and deliver queued notifications when they're due."""
        while self._is_active: # While worker is active
            async with self._queue_event: # When queue event is awake - proceed
                if not self._schedule_queue: # if queue is empty - wait
                    await self._queue_event.wait()
                    continue

                when_ts, _, notification = self._schedule_queue[0] # get head of queue values
                delay = when_ts - now_utc().timestamp() # Time until head's effective send time

                if delay > 0: # If time until head effective send time - queue event waits until then
                    try:
                        await asyncio.wait_for(self._queue_event.wait(), timeout=delay)
                        continue
                    except asyncio.TimeoutError:
                        pass

                heapq.heappop(self._schedule_queue) # else pop queue head

            # Outside lock: If effective time - send notification queue head
            try:
                await deliver(notification=notification)
                print(f"{notification.id} delivered at {now_utc()}")
            except Exception as ex:
                print(f"Delivery failed for {notification.id}: {ex}")
