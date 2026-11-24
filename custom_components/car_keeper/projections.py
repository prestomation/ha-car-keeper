"""The shape of each read reply.

Every read is open to every user, so this module hides no field. It shapes the
document for a reader: it copies each record, so a caller cannot change the
stored document, and it adds the values that the reader needs and the document
does not store. The tab, the cards and the read services use the same function,
so they show the same data.

This module is pure. It imports no Home Assistant code.
"""

from __future__ import annotations

import copy
from typing import Any


def project_state(state: dict[str, Any], *, tab: bool, revision: int) -> dict[str, Any]:
    """The whole document for a reader, with the tab state and the revision."""
    out = copy.deepcopy(state)
    out["tab"] = tab
    out["revision"] = revision
    return out
