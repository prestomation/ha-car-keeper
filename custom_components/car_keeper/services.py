"""The ``car_keeper.*`` services and the 1 gate that both surfaces use.

``api_surface.SERVICES`` is the model. :func:`async_register_services` registers
each service of it, with the field schema of :data:`SERVICE_FIELDS` and the
handler of :data:`SERVICE_HANDLERS`. The websocket twin of each service calls
:func:`async_run` too, so the admin gate is the same on both paths.

A call with no user comes from an automation or the core, and it is trusted.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv

from . import import_export, models, projections, readings, templates
from .api_surface import SERVICES, ServiceSpec
from .backend_i18n import resolve_exception, resolve_string
from .const import DOMAIN, UNITS
from .coordinator import CarCoordinator, find_coordinator
from .models import CarKeeperError
from .store import CarStore, today

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Actor:
    """The caller of 1 operation."""

    user_id: str | None
    is_admin: bool


@dataclass(frozen=True)
class Ctx:
    """The context of 1 operation: Home Assistant, the coordinator and the caller."""

    hass: HomeAssistant
    coordinator: CarCoordinator
    actor: Actor

    @property
    def store(self) -> CarStore:
        """The store."""
        return self.coordinator.store

    def car_reply(self, car_id: str) -> dict[str, Any]:
        """A car in a reply, with its computed values."""
        return projections.project_car(self.store.state, car_id, today())["car"]

    def item_reply(self, item_id: str) -> dict[str, Any]:
        """An item in a reply, with its evaluation."""
        item = self.store.item(item_id)
        view = projections.project_car(self.store.state, item["car_id"], today())
        return next(i for i in view["items"] if i["id"] == item_id)

    def service_reply(self, service_id: str) -> dict[str, Any]:
        """A service record in a reply."""
        return self.store.service(service_id)


Handler = Callable[[Ctx, dict[str, Any]], Awaitable[dict[str, Any]]]


async def actor_for_call(hass: HomeAssistant, call: ServiceCall) -> Actor:
    """The caller of a service call. A call with no user is trusted."""
    user_id = call.context.user_id
    if user_id is None:
        return Actor(user_id=None, is_admin=True)
    user = await hass.auth.async_get_user(user_id)
    return Actor(user_id=user_id, is_admin=bool(user and user.is_admin))


# ── Field schemas ────────────────────────────────────────────────────────────

_OPT_STR = vol.Any(None, cv.string)
_OPT_NUM = vol.Any(None, vol.Coerce(float))
_OPT_INT = vol.Any(None, vol.Coerce(int))
_STR_LIST = vol.All(cv.ensure_list, [cv.string])
_UNIT = vol.In(UNITS)

_CAR_FIELDS: dict[Any, Any] = {
    vol.Optional("make"): _OPT_STR,
    vol.Optional("model"): _OPT_STR,
    vol.Optional("year"): _OPT_INT,
    vol.Optional("trim"): _OPT_STR,
    vol.Optional("fuel"): vol.In(models.FUELS),
    vol.Optional("vin"): _OPT_STR,
    vol.Optional("plate"): _OPT_STR,
    vol.Optional("area_id"): _OPT_STR,
    vol.Optional("notes"): _OPT_STR,
    vol.Optional("lead_distance"): _OPT_NUM,
    vol.Optional("lead_days"): _OPT_INT,
    vol.Optional("unit"): _UNIT,
    vol.Optional("odometer_source"): vol.In(readings.SOURCES),
    vol.Optional("odometer_entity_id"): vol.Any(None, cv.entity_id),
}
_ITEM_FIELDS: dict[Any, Any] = {
    vol.Optional("kind"): vol.In(models.ITEM_KINDS),
    vol.Optional("interval_distance"): _OPT_NUM,
    vol.Optional("interval_months"): _OPT_INT,
    vol.Optional("due_date"): _OPT_STR,
    vol.Optional("lead_distance"): _OPT_NUM,
    vol.Optional("lead_days"): _OPT_INT,
    vol.Optional("notes"): _OPT_STR,
    vol.Optional("enabled"): cv.boolean,
    vol.Optional("add_task"): cv.boolean,
}
_SERVICE_FIELDS: dict[Any, Any] = {
    vol.Optional("date"): _OPT_STR,
    vol.Optional("reading"): _OPT_NUM,
    vol.Optional("items"): _STR_LIST,
    vol.Optional("shop"): _OPT_STR,
    vol.Optional("notes"): _OPT_STR,
    vol.Optional("who"): _OPT_STR,
    vol.Optional("cost"): _OPT_NUM,
}
_CAR_ID = {vol.Required("car_id"): cv.string}
_TEMPLATES = {
    vol.Optional("starter_jobs"): _STR_LIST,
    vol.Optional("due_dates"): vol.Schema({cv.string: cv.string}),
}

SERVICE_FIELDS: dict[str, dict[Any, Any]] = {
    "add_car": {
        vol.Required("name"): cv.string,
        **_CAR_FIELDS,
        vol.Optional("odometer"): _OPT_NUM,
        **_TEMPLATES,
    },
    "update_car": {**_CAR_ID, vol.Optional("name"): cv.string, **_CAR_FIELDS},
    "delete_car": {**_CAR_ID},
    "set_odometer": {**_CAR_ID, vol.Required("value"): vol.Coerce(float)},
    "correct_odometer": {
        **_CAR_ID,
        vol.Required("value"): vol.Coerce(float),
        vol.Optional("offset"): _OPT_NUM,
    },
    "add_item": {
        **_CAR_ID,
        vol.Required("name"): cv.string,
        **_ITEM_FIELDS,
        vol.Optional("last_date"): _OPT_STR,
        vol.Optional("last_reading"): _OPT_NUM,
    },
    "update_item": {
        vol.Required("item_id"): cv.string,
        vol.Optional("name"): cv.string,
        **_ITEM_FIELDS,
    },
    "delete_item": {vol.Required("item_id"): cv.string},
    "apply_templates": {
        **_CAR_ID,
        vol.Required("starter_jobs"): _STR_LIST,
        vol.Optional("due_dates"): vol.Schema({cv.string: cv.string}),
    },
    "log_service": {**_CAR_ID, **_SERVICE_FIELDS},
    "update_service": {
        vol.Required("service_id"): cv.string,
        **_SERVICE_FIELDS,
        vol.Optional("parts_used"): list,
    },
    "delete_service": {vol.Required("service_id"): cv.string},
    "set_settings": {
        vol.Optional("unit"): _UNIT,
        vol.Optional("templates"): dict,
    },
    "export_data": {vol.Optional("files_dir"): _OPT_STR},
    "import_data": {
        vol.Required("document"): dict,
        vol.Optional("dry_run", default=False): cv.boolean,
        vol.Optional("files_dir"): _OPT_STR,
    },
    "list_cars": {},
    "get_car": {**_CAR_ID},
    "list_items": {vol.Optional("car_id"): cv.string},
    "list_services": {vol.Optional("car_id"): cv.string},
}


# ── Handlers ─────────────────────────────────────────────────────────────────


def _names(hass: HomeAssistant) -> dict[str, str]:
    """The name of each starter job in the language of Home Assistant."""
    lang = hass.config.language
    return {t.id: resolve_string(lang, f"template.{t.id}") for t in templates.TEMPLATES}


def _clean(data: dict[str, Any], *drop: str) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k not in drop}


async def _add_car(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    car = await ctx.store.add_car(
        _clean(data, "starter_jobs", "due_dates"),
        starter=data.get("starter_jobs") or (),
        names=_names(ctx.hass),
        due_dates=data.get("due_dates"),
        by=ctx.actor.user_id,
    )
    return {"car": ctx.car_reply(car["id"])}


async def _update_car(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    car = await ctx.store.update_car(data["car_id"], _clean(data, "car_id"))
    return {"car": ctx.car_reply(car["id"])}


async def _delete_car(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    car = await ctx.store.delete_car(data["car_id"])
    return {"car_id": car["id"]}


async def _set_odometer(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    await ctx.store.set_odometer(data["car_id"], data["value"], by=ctx.actor.user_id)
    return {"car": ctx.car_reply(data["car_id"])}


async def _correct_odometer(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    await ctx.store.correct_odometer(
        data["car_id"], data["value"], offset=data.get("offset"), by=ctx.actor.user_id
    )
    ctx.coordinator.clear_odometer_issue(data["car_id"])
    return {"car": ctx.car_reply(data["car_id"])}


async def _add_item(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    item = await ctx.store.add_item(data["car_id"], _clean(data, "car_id"))
    return {"item": ctx.item_reply(item["id"])}


async def _update_item(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    item = await ctx.store.update_item(data["item_id"], _clean(data, "item_id"))
    return {"item": ctx.item_reply(item["id"])}


async def _delete_item(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    item = await ctx.store.delete_item(data["item_id"])
    return {"item_id": item["id"]}


async def _apply_templates(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    items = await ctx.store.apply_templates(
        data["car_id"],
        list(data["starter_jobs"]),
        names=_names(ctx.hass),
        due_dates=data.get("due_dates"),
    )
    return {"items": [ctx.item_reply(i["id"]) for i in items]}


async def _log_service(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    service = await ctx.store.log_service(
        data["car_id"], _clean(data, "car_id"), by=ctx.actor.user_id
    )
    return {"service": ctx.service_reply(service["id"])}


async def _update_service(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    service = await ctx.store.update_service(
        data["service_id"], _clean(data, "service_id")
    )
    return {"service": ctx.service_reply(service["id"])}


async def _delete_service(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    service = await ctx.store.delete_service(data["service_id"])
    return {"service_id": service["id"]}


async def _set_settings(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    changes = dict(data)
    if "templates" in changes:
        changes["templates"] = templates.clean_overrides(changes["templates"])
    settings = await ctx.store.set_settings(changes)
    return {"settings": settings}


async def _export_data(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    return import_export.export_document(ctx.store.state, ctx.coordinator.version)


def _problem_text(hass: HomeAssistant, problem: dict[str, Any]) -> dict[str, Any]:
    return {
        "level": problem["level"],
        "path": problem["path"],
        "message": resolve_exception(
            hass.config.language, problem["key"], **problem["params"]
        ),
    }


async def _import_data(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    entity_ids = {state.entity_id for state in ctx.hass.states.async_all()}
    plan = import_export.plan_import(
        ctx.store.state, data["document"], entity_ids=entity_ids
    )
    report = plan["report"]
    if report["ok"] and not data["dry_run"]:
        await ctx.store.import_plan(plan)
    records = sum(
        count["created"] + count["updated"] for count in report["counts"].values()
    )
    return {
        "ok": report["ok"],
        "dry_run": data["dry_run"],
        "counts": report["counts"],
        "records": records,
        "problems": [_problem_text(ctx.hass, p) for p in report["problems"]],
    }


async def _list_cars(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    state = ctx.store.state
    day = today()
    cars = []
    for car_id in sorted(
        state["cars"], key=lambda c: state["cars"][c]["name"].casefold()
    ):
        car = projections.project_car(state, car_id, day)["car"]
        cars.append(car)
    return {"cars": cars}


async def _get_car(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    ctx.store.car(data["car_id"])
    return projections.project_car(ctx.store.state, data["car_id"], today())


async def _list_items(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    state = ctx.store.state
    car_ids = [data["car_id"]] if data.get("car_id") else list(state["cars"])
    if data.get("car_id"):
        ctx.store.car(data["car_id"])
    day = today()
    items = []
    for car_id in car_ids:
        items += projections.project_car(state, car_id, day)["items"]
    return {"items": items}


async def _list_services(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    state = ctx.store.state
    car_ids = [data["car_id"]] if data.get("car_id") else list(state["cars"])
    if data.get("car_id"):
        ctx.store.car(data["car_id"])
    day = today()
    services = []
    for car_id in car_ids:
        services += projections.project_car(state, car_id, day)["services"]
    services.sort(key=lambda s: (s["date"], s.get("logged") or ""), reverse=True)
    return {"services": services}


SERVICE_HANDLERS: dict[str, Handler] = {
    "add_car": _add_car,
    "update_car": _update_car,
    "delete_car": _delete_car,
    "set_odometer": _set_odometer,
    "correct_odometer": _correct_odometer,
    "add_item": _add_item,
    "update_item": _update_item,
    "delete_item": _delete_item,
    "apply_templates": _apply_templates,
    "log_service": _log_service,
    "update_service": _update_service,
    "delete_service": _delete_service,
    "set_settings": _set_settings,
    "export_data": _export_data,
    "import_data": _import_data,
    "list_cars": _list_cars,
    "get_car": _get_car,
    "list_items": _list_items,
    "list_services": _list_services,
}

_RESPONSES = {
    "none": SupportsResponse.NONE,
    "optional": SupportsResponse.OPTIONAL,
    "only": SupportsResponse.ONLY,
}


def coordinator_or_error(hass: HomeAssistant) -> CarCoordinator:
    """The loaded coordinator, or the localized ``not_loaded`` error."""
    coordinator = find_coordinator(hass)
    if coordinator is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="not_loaded"
        )
    return coordinator


async def async_run(
    hass: HomeAssistant, spec: ServiceSpec, actor: Actor, data: dict[str, Any]
) -> dict[str, Any]:
    """Run 1 operation for *actor*, with the gate of *spec*.

    Raise ``Unauthorized`` for a refused caller, and :class:`CarKeeperError` for
    input that Car Keeper refuses.
    """
    if spec.admin_only and not actor.is_admin:
        raise Unauthorized(context=None)
    coordinator = coordinator_or_error(hass)
    ctx = Ctx(hass, coordinator, actor)
    return await SERVICE_HANDLERS[spec.name](ctx, data)


def _service_handler(
    hass: HomeAssistant, spec: ServiceSpec
) -> Callable[[ServiceCall], Coroutine[Any, Any, ServiceResponse]]:
    async def handle(call: ServiceCall) -> ServiceResponse:
        actor = await actor_for_call(hass, call)
        try:
            result = await async_run(hass, spec, actor, dict(call.data))
        except Unauthorized as err:
            raise Unauthorized(context=call.context) from err
        except CarKeeperError as err:
            raise service_error(err) from err
        return result if call.return_response else None

    return handle


def service_error(err: CarKeeperError) -> ServiceValidationError:
    """The Home Assistant error for a Car Keeper error."""
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=err.key,
        translation_placeholders=err.placeholders,
    )


def async_register_services(hass: HomeAssistant) -> None:
    """Register each service of ``api_surface.SERVICES``."""
    for spec in SERVICES:
        hass.services.async_register(
            DOMAIN,
            spec.name,
            _service_handler(hass, spec),
            schema=vol.Schema(SERVICE_FIELDS[spec.name]),
            supports_response=_RESPONSES[spec.response],
        )
