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
    ServiceSpec("add_car", response="optional", **_ADMIN),
    ServiceSpec("update_car", response="optional", **_ADMIN),
    ServiceSpec("delete_car", response="optional", **_ADMIN),
    ServiceSpec("set_odometer", response="optional"),
    ServiceSpec("correct_odometer", response="optional", **_ADMIN),
    ServiceSpec("add_item", response="optional", **_ADMIN),
    ServiceSpec("update_item", response="optional", **_ADMIN),
    ServiceSpec("delete_item", response="optional", **_ADMIN),
    ServiceSpec("apply_templates", response="optional", **_ADMIN),
    ServiceSpec("log_service", response="optional"),
    ServiceSpec("update_service", response="optional", **_ADMIN),
    ServiceSpec("delete_service", response="optional", **_ADMIN),
    ServiceSpec("set_settings", response="optional", **_ADMIN),
    ServiceSpec("export_data", response="only", **_ADMIN),
    ServiceSpec("import_data", response="only", **_ADMIN),
    ServiceSpec("list_cars", response="only"),
    ServiceSpec("get_car", response="only"),
    ServiceSpec("list_items", response="only"),
    ServiceSpec("list_services", response="only"),
)

#: The services that ``async_unload_entry`` removes.
SERVICE_NAMES: tuple[str, ...] = tuple(spec.name for spec in SERVICES)

#: The read services. Every user can call them. They have no websocket twin,
#: because ``get_state`` gives the same data to the tab and the cards.
READ_SERVICES: tuple[str, ...] = ("list_cars", "get_car", "list_items", "list_services")


# ── Event payloads ───────────────────────────────────────────────────────────
#
# One spine per payload shape. The drift test calls the builders in events.py
# and compares the keys.

_ORIGIN = Field("origin", "str | None", "The origin marker of the caller.")

_CAR = Field("car_id", "str", "The id of the car.")

PAYLOAD_SPINES: dict[str, tuple[Field, ...]] = {
    "car": (_CAR, Field("name", "str", "The name of the car."), _ORIGIN),
    "odometer": (
        _CAR,
        Field("name", "str", "The name of the car."),
        Field("value", "float", "The reading, in the unit of the car."),
        Field("unit", "str", "`km` or `mi`."),
        Field("source", "str", "`manual`, `entity`, `service` or `correction`."),
        _ORIGIN,
    ),
    "item": (
        _CAR,
        Field("item_id", "str", "The id of the job."),
        Field("name", "str", "The name of the job."),
        _ORIGIN,
    ),
    "due": (
        _CAR,
        Field("car_name", "str", "The name of the car."),
        Field("item_id", "str", "The id of the job."),
        Field("name", "str", "The name of the job."),
        Field("status", "str", "`soon` or `overdue`."),
        Field(
            "first", "str | None", "`distance` or `date`: the limit that comes first."
        ),
        Field("distance_limit", "float | None", "The reading at which the job is due."),
        Field("distance_left", "float | None", "The distance to that reading."),
        Field("date_limit", "str | None", "The date at which the job is due."),
        Field("days_left", "int | None", "The days to that date."),
        Field("unit", "str", "`km` or `mi`."),
    ),
    "service": (
        _CAR,
        Field("service_id", "str", "The id of the service record."),
        Field("date", "str", "The date of the service, `YYYY-MM-DD`."),
        Field("reading", "float | None", "The odometer at the service."),
        Field("items", "list[str]", "The ids of the jobs that the service did."),
        Field("shop", "str", "The shop."),
        Field("cost", "float | None", "The cost of the visit."),
        _ORIGIN,
    ),
    "settings": (
        Field("changed_fields", "list[str]", "The settings that changed."),
        _ORIGIN,
    ),
    "data_import": (
        Field(
            "counts",
            "dict[str, dict[str, int]]",
            "created, updated and unchanged for each section.",
        ),
        _ORIGIN,
    ),
}

_CHANGED = (Field("changed_fields", "list[str]", "The fields that changed."),)


def _event(
    const_name: str, payload: str, summary: str, extra: tuple[Field, ...] = ()
) -> EventSpec:
    return EventSpec(
        getattr(const, const_name), const_name, "fired", payload, summary, extra
    )


# ── Events ───────────────────────────────────────────────────────────────────

EVENTS: tuple[EventSpec, ...] = (
    _event("EVENT_CAR_ADDED", "car", "A car was added."),
    _event("EVENT_CAR_UPDATED", "car", "A car changed.", _CHANGED),
    _event("EVENT_CAR_REMOVED", "car", "A car was deleted."),
    _event("EVENT_ODOMETER_UPDATED", "odometer", "A reading was stored."),
    _event("EVENT_ITEM_ADDED", "item", "A job was added."),
    _event("EVENT_ITEM_UPDATED", "item", "A job changed.", _CHANGED),
    _event("EVENT_ITEM_REMOVED", "item", "A job was deleted."),
    _event("EVENT_ITEM_DUE_SOON", "due", "A job entered its warning window."),
    _event("EVENT_ITEM_OVERDUE", "due", "A job passed a limit."),
    _event("EVENT_SERVICE_LOGGED", "service", "A service record was added."),
    _event("EVENT_SERVICE_UPDATED", "service", "A service record changed.", _CHANGED),
    _event("EVENT_SERVICE_REMOVED", "service", "A service record was deleted."),
    _event("EVENT_SETTINGS_UPDATED", "settings", "A setting changed."),
    _event("EVENT_DATA_IMPORTED", "data_import", "An import was written."),
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

ENTITY_PLATFORMS: tuple[EntityPlatformSpec, ...] = (
    EntityPlatformSpec(
        "sensor",
        translation_keys=("odometer", "next_due_distance", "next_due_date", "status"),
        attributes=(
            Field(
                "reading",
                "float | None",
                "Odometer: the reading in the unit of the car.",
            ),
            Field("unit", "str", "Odometer: `km` or `mi`."),
            Field("source", "str", "Odometer: `manual` or `entity`."),
            Field("updated", "str | None", "Odometer: the time of the reading."),
            Field("item_id", "str | None", "Next due: the id of the job."),
            Field("job", "str | None", "Next due: the name of the job."),
            Field("distance_limit", "float | None", "Next due distance: the limit."),
            Field("days_left", "int | None", "Next due date: the days to the limit."),
            Field("status", "str | None", "Next due: the status of the job."),
            Field("next_item_id", "str | None", "Status: the id of the next job."),
            Field("next_job", "str | None", "Status: the name of the next job."),
            Field("due_count", "int", "Status: the jobs that are soon or overdue."),
            Field("due_jobs", "list[str]", "Status: the names of those jobs."),
            Field("daily_distance", "float | None", "Status: the distance a day."),
        ),
    ),
    EntityPlatformSpec(
        "binary_sensor",
        translation_keys=("overdue",),
        attributes=(Field("overdue_jobs", "list[str]", "The jobs that are overdue."),),
    ),
    EntityPlatformSpec("todo", translation_keys=("jobs",)),
)


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
        "published",
        "Each car has a device with 4 sensors, an overdue binary sensor and a "
        "`todo` list of the jobs that are due.",
    ),
    SurfaceKind(
        "Entity attributes",
        "published",
        "The odometer sensor has the attribute `reading`. Home Keeper tasks read it.",
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
        "the tab, and when an odometer sensor reports lower values.",
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
