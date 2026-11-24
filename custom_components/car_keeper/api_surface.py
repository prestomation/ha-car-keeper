"""The index of every surface that an integrator can use.

The public API of Car Keeper is in registries that do not know about
each other: the services in ``services.py``, the bus events in ``const.py`` with
payloads from ``events.py``, the websocket commands in ``websocket_api.py``, the
entity platforms in ``const.PLATFORMS``, and the static path in
``frontend_assets.py``. This module declares each surface once.

The runtime reads this model. ``services.py`` registers each service of
:data:`SERVICES` and applies its admin gate, ``websocket_api.py`` registers the
websocket twin of each service from :data:`WEBSOCKET_COMMANDS`, and
``async_unload_entry`` removes :data:`SERVICE_NAMES`. The unit test
``tests/unit/test_api_surface.py`` reads the source and fails on drift.

**The model holds names and structure only.** The labels and descriptions are in
``services.yaml`` and ``strings.json``. :attr:`EventSpec.summary` is the 1
exception, because a bus event has no Home Assistant string source.

The module is pure. It imports no Home Assistant code, and only ``const`` from the
integration.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import const

# ── Descriptors ──────────────────────────────────────────────────────────────
#
# Each table is a tuple, never a set, so that each rendering has the same order.


@dataclass(frozen=True, slots=True)
class Field:
    """One key in an event payload or an entity attribute map."""

    name: str
    type: str = ""
    """Shown as is, such as ``"str | None"``. Never parsed."""
    note: str = ""


@dataclass(frozen=True, slots=True)
class ServiceSpec:
    """A ``car_keeper.*`` service.

    ``name`` is the key in ``services.yaml``, in ``strings.json`` ``services`` and
    in the handler table of ``services.py``.
    """

    name: str
    admin_only: bool = False
    """The service handler rejects a non-admin user with ``Unauthorized``."""
    response: str = "none"
    """``"none"``, ``"optional"`` or ``"only"``, as ``SupportsResponse``."""


@dataclass(frozen=True, slots=True)
class EventSpec:
    """A bus event that the integration fires, or one that it listens for."""

    name: str
    """The value of the ``const`` attribute. Never a typed copy."""
    const_name: str
    """The ``const`` attribute that holds the name."""
    direction: str
    """``"fired"`` or ``"listened"``."""
    payload: str
    """A key of :data:`PAYLOAD_SPINES`, or ``"none"``."""
    summary: str = ""
    """When the event fires. Required for a fired event."""
    extra: tuple[Field, ...] = ()
    """The keys that the event adds to its spine."""


@dataclass(frozen=True, slots=True)
class DeviceTriggerSpec:
    """A device trigger for a bus event. Car Keeper has none."""

    type: str
    event: str
    scope: str


@dataclass(frozen=True, slots=True)
class EntityPlatformSpec:
    """An entity platform and the state attributes of its entities."""

    platform: str
    translation_keys: tuple[str, ...] = ()
    """Keys in ``strings.json`` ``entity.<platform>``."""
    attributes: tuple[Field, ...] = ()


@dataclass(frozen=True, slots=True)
class WebsocketSpec:
    """A websocket command of the tab and the card.

    A command with a ``service`` is the twin of that service: it takes the same
    fields, has the same gate and calls the same code. The runtime registers it
    from this table.
    """

    type: str
    admin_only: bool = False
    service: str | None = None


@dataclass(frozen=True, slots=True)
class HttpViewSpec:
    """An HTTP route that the integration registers."""

    name: str
    url: str
    methods: tuple[str, ...]
    requires_auth: bool = True
    admin_methods: tuple[str, ...] = ()
    """The methods that only an admin user can call."""


@dataclass(frozen=True, slots=True)
class OptionSpec:
    """A config entry option key."""

    key: str
    in_flow: bool
    """Whether the options flow shows it."""


@dataclass(frozen=True, slots=True)
class SurfaceKind:
    """One kind of Home Assistant integration surface, and the stance of Car Keeper.

    The table lists also the kinds that Car Keeper does not offer, each with a
    reason. A list of only the offered kinds cannot show what is missing.
    """

    kind: str
    status: str
    """``"published"``, ``"internal"``, ``"not_applicable"`` or ``"deferred"``."""
    note: str
    """One sentence. Required."""


STATUSES = ("published", "internal", "not_applicable", "deferred")


# ── Services ─────────────────────────────────────────────────────────────────

_ADMIN = {"admin_only": True}

SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec("set_settings", response="optional", **_ADMIN),
)

#: The services that ``async_unload_entry`` removes.
SERVICE_NAMES: tuple[str, ...] = tuple(spec.name for spec in SERVICES)

#: The read services. Each reply goes through ``projections``. They have no
#: websocket twin, because ``get_state`` gives the same data to the tab and cards.
READ_SERVICES: tuple[str, ...] = ()


# ── Event payloads ───────────────────────────────────────────────────────────
#
# One spine per payload shape. The drift test calls the builders in events.py
# and compares the keys.

_ORIGIN = Field("origin", "str | None", "The origin marker of the caller.")

PAYLOAD_SPINES: dict[str, tuple[Field, ...]] = {
    "settings": (
        Field("changed_fields", "list[str]", "The settings that changed."),
        _ORIGIN,
    ),
}


def _event(
    const_name: str, payload: str, summary: str, extra: tuple[Field, ...] = ()
) -> EventSpec:
    return EventSpec(
        getattr(const, const_name), const_name, "fired", payload, summary, extra
    )


# ── Events ───────────────────────────────────────────────────────────────────

EVENTS: tuple[EventSpec, ...] = (
    _event("EVENT_SETTINGS_UPDATED", "settings", "A setting changed."),
    EventSpec(
        const.HOME_KEEPER_EVENT_REGISTER_COMPANIONS,
        "HOME_KEEPER_EVENT_REGISTER_COMPANIONS",
        "listened",
        "none",
        summary="Car Keeper registers as a companion again.",
    ),
)


# ── Device triggers ──────────────────────────────────────────────────────────

DEVICE_TRIGGERS: tuple[DeviceTriggerSpec, ...] = ()


# ── Entity platforms ─────────────────────────────────────────────────────────

ENTITY_PLATFORMS: tuple[EntityPlatformSpec, ...] = ()


# ── Websocket commands (internal) ────────────────────────────────────────────

WEBSOCKET_COMMANDS: tuple[WebsocketSpec, ...] = (
    WebsocketSpec(f"{const.DOMAIN}/get_state"),
    WebsocketSpec(f"{const.DOMAIN}/subscribe"),
    *(
        WebsocketSpec(
            f"{const.DOMAIN}/{spec.name}", admin_only=spec.admin_only, service=spec.name
        )
        for spec in SERVICES
        if spec.name not in READ_SERVICES
    ),
)


# ── HTTP routes (internal) ───────────────────────────────────────────────────

HTTP_VIEWS: tuple[HttpViewSpec, ...] = (
    HttpViewSpec(
        "static",
        const.STATIC_URL,
        ("GET",),
        # Home Assistant serves a static path before authentication, so only the
        # built bundles in frontend/dist/ are in this path.
        requires_auth=False,
    ),
)


# ── Config entry options ─────────────────────────────────────────────────────

OPTIONS: tuple[OptionSpec, ...] = (OptionSpec(const.CONF_UNIT, in_flow=True),)


# ── The whole surface space ──────────────────────────────────────────────────

SURFACE_KINDS: tuple[SurfaceKind, ...] = (
    SurfaceKind(
        "Actions (services)",
        "published",
        "Each operation that changes or exports Car Keeper data is a "
        "`car_keeper.*` service.",
    ),
    SurfaceKind(
        "Bus events",
        "published",
        "Each state change fires a `car_keeper_<noun>_<verb>` event with a "
        "payload from a pure builder.",
    ),
    SurfaceKind(
        "Device triggers",
        "not_applicable",
        "The bus events and the entities give the triggers of an automation.",
    ),
    SurfaceKind(
        "Device conditions",
        "not_applicable",
        "The sensors of each car give the state that a condition reads.",
    ),
    SurfaceKind(
        "Device actions",
        "not_applicable",
        "The services cover each operation and take a car id directly.",
    ),
    SurfaceKind(
        "Entity platforms",
        "not_applicable",
        "Car Keeper has no entity platform yet.",
    ),
    SurfaceKind(
        "Entity attributes",
        "not_applicable",
        "Car Keeper has no entity yet.",
    ),
    SurfaceKind(
        "Config entry options",
        "published",
        "The distance unit of a new car.",
    ),
    SurfaceKind(
        "Config flow",
        "published",
        "A single-instance setup flow with a distance unit field, and an options "
        "flow that changes it.",
    ),
    SurfaceKind(
        "Websocket commands",
        "internal",
        "The tab and the cards read the state and call the twin of each service.",
    ),
    SurfaceKind(
        "HTTP routes",
        "internal",
        "A static path for the bundles.",
    ),
    SurfaceKind(
        "Diagnostics",
        "published",
        "The config entry gives a diagnostics download, with the VIN and the plate "
        "redacted.",
    ),
    SurfaceKind(
        "Reauth / reconfigure flows",
        "not_applicable",
        "Car Keeper has no credential. The storage is local.",
    ),
    SurfaceKind(
        "Repairs / issue registry",
        "published",
        "An issue shows when Home Keeper is missing, not set up or too old for "
        "the tab.",
    ),
    SurfaceKind(
        "Discovery",
        "not_applicable",
        "No device or service on the network is a car record.",
    ),
    SurfaceKind(
        "Home Keeper panel tab",
        "internal",
        "The admin UI is a tab in the Home Keeper panel, registered through the "
        "Python API of Home Keeper.",
    ),
)


def events_by_payload(payload: str) -> tuple[EventSpec, ...]:
    """Return every fired event sharing one payload shape, in declaration order."""
    return tuple(
        spec for spec in EVENTS if spec.direction == "fired" and spec.payload == payload
    )


__all__ = [
    "DEVICE_TRIGGERS",
    "ENTITY_PLATFORMS",
    "EVENTS",
    "HTTP_VIEWS",
    "OPTIONS",
    "PAYLOAD_SPINES",
    "READ_SERVICES",
    "SERVICES",
    "SERVICE_NAMES",
    "STATUSES",
    "SURFACE_KINDS",
    "WEBSOCKET_COMMANDS",
    "DeviceTriggerSpec",
    "EntityPlatformSpec",
    "EventSpec",
    "Field",
    "HttpViewSpec",
    "OptionSpec",
    "ServiceSpec",
    "SurfaceKind",
    "WebsocketSpec",
    "events_by_payload",
]
