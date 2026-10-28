from services.login_throttle import LoginThrottle


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(max_failures=3, window_seconds=60):
    clock = FakeClock()
    return LoginThrottle(max_failures, window_seconds, clock=clock), clock


def test_not_blocked_before_the_limit():
    throttle, _ = make()
    throttle.record_failure('a')
    throttle.record_failure('a')
    assert not throttle.is_blocked('a')


def test_blocked_once_the_limit_is_reached():
    throttle, _ = make()
    for _ in range(3):
        throttle.record_failure('a')
    assert throttle.is_blocked('a')


def test_block_lifts_when_old_failures_leave_the_window():
    throttle, clock = make()
    for _ in range(3):
        throttle.record_failure('a')
    clock.now += 61
    assert not throttle.is_blocked('a')


def test_failures_spread_beyond_the_window_do_not_add_up():
    throttle, clock = make()
    throttle.record_failure('a')
    throttle.record_failure('a')
    clock.now += 61
    throttle.record_failure('a')
    assert not throttle.is_blocked('a')


def test_success_clears_the_record():
    throttle, _ = make()
    for _ in range(3):
        throttle.record_failure('a')
    throttle.reset('a')
    assert not throttle.is_blocked('a')


def test_keys_are_independent():
    throttle, _ = make()
    for _ in range(3):
        throttle.record_failure('a')
    assert throttle.is_blocked('a')
    assert not throttle.is_blocked('b')
