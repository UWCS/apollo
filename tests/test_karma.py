import datetime as datetime_module
from datetime import datetime, timezone

from karma.karma import is_in_cooldown
from models.karma import KarmaChange

_TIMEOUT = 60


def build_karma_change(created_at: datetime) -> KarmaChange:
    return KarmaChange(
        karma_id=1,
        user_id=1,
        message_id=1,
        reason=None,
        change=1,
        score=1,
        created_at=created_at,
    )


def test_is_in_cooldown():
    last_change = build_karma_change(datetime.now(timezone.utc))
    assert is_in_cooldown(last_change, _TIMEOUT)


def test_not_is_in_cooldown():
    last_change = build_karma_change(
        datetime.now(timezone.utc) - datetime_module.timedelta(seconds=100)
    )
    assert not is_in_cooldown(last_change, _TIMEOUT)
