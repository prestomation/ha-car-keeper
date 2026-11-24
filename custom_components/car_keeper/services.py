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

from .api_surface import SERVICES, ServiceSpec
from .const import DOMAIN, UNITS
from .coordinator import CarCoordinator, find_coordinator
from .models import CarKeeperError
from .store import CarStore

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


Handler = Callable[[Ctx, dict[str, Any]], Awaitable[dict[str, Any]]]


async def actor_for_call(hass: HomeAssistant, call: ServiceCall) -> Actor:
    """The caller of a service call. A call with no user is trusted."""
    user_id = call.context.user_id
    if user_id is None:
        return Actor(user_id=None, is_admin=True)
    user = await hass.auth.async_get_user(user_id)
    return Actor(user_id=user_id, is_admin=bool(user and user.is_admin))


# ── Field schemas ────────────────────────────────────────────────────────────

SERVICE_FIELDS: dict[str, dict[Any, Any]] = {
    "set_settings": {vol.Optional("unit"): vol.In(UNITS)},
}


# ── Handlers ─────────────────────────────────────────────────────────────────


async def _set_settings(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    settings = await ctx.store.set_settings(data)
    return {"settings": settings}


SERVICE_HANDLERS: dict[str, Handler] = {
    "set_settings": _set_settings,
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
