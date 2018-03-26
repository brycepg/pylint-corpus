"""Helpers for Home Assistant dispatcher & internal component/platform."""
import logging

from homeassistant.core import callback
from homeassistant.loader import bind_hass
from homeassistant.util.async import run_callback_threadsafe


_LOGGER = logging.getLogger(__name__)
DATA_DISPATCHER = 'dispatcher'


@bind_hass
def dispatcher_connect(hass, signal, target):
    """Connect a callable function to a signal."""
    async_unsub = run_callback_threadsafe(
        hass.loop, async_dispatcher_connect, hass, signal, target).result()

    def remove_dispatcher():
        """Remove signal listener."""
        run_callback_threadsafe(hass.loop, async_unsub).result()

    return remove_dispatcher


@callback
@bind_hass
def async_dispatcher_connect(hass, signal, target):
    """Connect a callable function to a signal.

    This method must be run in the event loop.
    """
    if DATA_DISPATCHER not in hass.data:
        hass.data[DATA_DISPATCHER] = {}

    if signal not in hass.data[DATA_DISPATCHER]:
        hass.data[DATA_DISPATCHER][signal] = []

    hass.data[DATA_DISPATCHER][signal].append(target)

    @callback
    def async_remove_dispatcher():
        """Remove signal listener."""
        try:
            hass.data[DATA_DISPATCHER][signal].remove(target)
        except (KeyError, ValueError):
            # KeyError is key target listener did not exist
            # ValueError if listener did not exist within signal
            _LOGGER.warning(
                "Unable to remove unknown dispatcher %s", target)

    return async_remove_dispatcher


@bind_hass
def dispatcher_send(hass, signal, *args):
    """Send signal and data."""
    hass.loop.call_soon_threadsafe(async_dispatcher_send, hass, signal, *args)


@callback
@bind_hass
def async_dispatcher_send(hass, signal, *args):
    """Send signal and data.

    This method must be run in the event loop.
    """
    target_list = hass.data.get(DATA_DISPATCHER, {}).get(signal, [])

    for target in target_list:
        hass.async_add_job(target, *args)
