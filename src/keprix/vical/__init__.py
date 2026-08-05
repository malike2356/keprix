"""Keprix viCal booking domain (Verlox Integrated Calendar behaviour).

Behavioural reference: propreneur-v2 Vcal module. Persistence mirrors the
workspace calendar JSON store under KEPRIX_DATA_DIR until a Postgres cutover.
"""

from keprix.vical.bookings import BookingLifecycle, BookingLifecycleError
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.slots import SlotEngine, TimeSlot
from keprix.vical.store import IsolationError, VicalStore, vical_store
from keprix.vical.types import (
    ACTIVE_BOOKING_STATUSES,
    BookingSource,
    BookingStatus,
    LocationMode,
    SessionOutcome,
    VcalAvailabilityRule,
    VcalBlackoutDate,
    VcalBooking,
    VcalEventType,
    VcalSlotLock,
)

__all__ = [
    "ACTIVE_BOOKING_STATUSES",
    "BookingLifecycle",
    "BookingLifecycleError",
    "BookingSource",
    "BookingStatus",
    "IsolationError",
    "LocationMode",
    "SessionOutcome",
    "SlotEngine",
    "TimeSlot",
    "VcalAvailabilityRule",
    "VcalBlackoutDate",
    "VcalBooking",
    "VcalEventType",
    "VcalSlotLock",
    "VicalStore",
    "ensure_default_consultation",
    "vical_store",
]
