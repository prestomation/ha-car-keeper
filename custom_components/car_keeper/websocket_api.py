"""The websocket commands of the Cars tab and the cards.

* ``car_keeper/get_state`` returns the whole document with the computed values
  (see ``projections.project_state``). Every user can read it.
* ``car_keeper/subscribe`` sends ``{"type": "changed", "revision": n}``
  after each store change. The client then calls ``get_state`` again.
* Each other command is the twin of a service, with the same name, the same
  fields and the same gate. It calls the same handler in ``services.py``. The
  table of twins is ``api_surface.WEBSOCKET_COMMANDS``.

A websocket error shows its message as is, so the message is resolved here in
the language of Home Assistant (``backend_i18n``).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import projections
from .api_surface import SERVICES, WEBSOCKET_COMMANDS
from .backend_i18n import resolve_exception
from .const import DOMAIN, SIGNAL_STORE_CHANGED
from .coordinator import find_coordinator
from .models import CarKeeperError
from .services import SERVICE_FIELDS, Actor, async_run
from .store import today

_SPECS = {spec.name: spec for spec in SERVICES}


def _error(
    connection: websocket_api.ActiveConnection,
    msg_id: int,
    hass: HomeAssistant,
    key: str,
    **placeholders: Any,
) -> None:
    connection.send_error(
        msg_id, key, resolve_exception(hass.config.language, key, **placeholders)
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands. A second call replaces them with the same ones."""
    websocket_api.async_register_command(hass, ws_get_state)
    websocket_api.async_register_command(hass, ws_subscribe)
    for command in WEBSOCKET_COMMANDS:
        if command.service is None:
            continue
        schema = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
            {
                vol.Required("type"): command.type,
                **SERVICE_FIELDS[command.service],
            }
        )
        websocket_api.async_register_command(
            hass, command.type, _service_command(command.service), schema
        )


def _service_command(service: str) -> websocket_api.const.WebSocketCommandHandler:
    spec = _SPECS[service]

    async def handle(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        data = {k: v for k, v in msg.items() if k not in ("id", "type")}
        # The connection user is the authority on the admin flag.
        actor = Actor(user_id=connection.user.id, is_admin=connection.user.is_admin)
        try:
            # ``async_run`` gates the call. Home Assistant answers its
            # ``Unauthorized`` with the ``unauthorized`` code.
            result = await async_run(hass, spec, actor, data)
        except CarKeeperError as err:
            _error(connection, msg["id"], hass, err.key, **err.placeholders)
            return
        except ServiceValidationError as err:
            _error(
                connection,
                msg["id"],
                hass,
                err.translation_key or "not_loaded",
                **(err.translation_placeholders or {}),
            )
            return
        connection.send_result(msg["id"], result)

    return websocket_api.async_response(handle)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get_state"})
@callback
def ws_get_state(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the document and the computed values."""
    coordinator = find_coordinator(hass)
    if coordinator is None:
        _error(connection, msg["id"], hass, "not_loaded")
        return
    connection.send_result(
        msg["id"],
        projections.project_state(
            coordinator.store.state,
            today=today(),
            tab=coordinator.tab_registered,
            revision=coordinator.store.revision,
        ),
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send ``{"type": "changed", "revision": n}`` after each store change."""
    coordinator = find_coordinator(hass)
    if coordinator is None:
        _error(connection, msg["id"], hass, "not_loaded")
        return

    @callback
    def _changed(revision: int) -> None:
        connection.send_message(
            websocket_api.event_message(
                msg["id"], {"type": "changed", "revision": revision}
            )
        )

    # A store listener that async_setup_entry adds sends the signal.
    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_STORE_CHANGED, _changed
    )
    connection.send_result(msg["id"], {"revision": coordinator.store.revision})
