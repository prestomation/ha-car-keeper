"""Settings shared by the stateful model tests.

``CK_STATEFUL_EXAMPLES`` sets how many runs each state machine gets. CI sets it high
(``test.yml``). The default keeps a local run short.
"""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

EXAMPLES = int(os.environ.get("CK_STATEFUL_EXAMPLES", "60"))

STATEFUL = settings(
    max_examples=EXAMPLES,
    stateful_step_count=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
