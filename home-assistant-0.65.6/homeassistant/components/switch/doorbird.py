"""Support for powering relays in a DoorBird video doorbell."""
import datetime
import logging

import voluptuous as vol

from homeassistant.components.doorbird import DOMAIN as DOORBIRD_DOMAIN
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchDevice
from homeassistant.const import CONF_SWITCHES
import homeassistant.helpers.config_validation as cv

DEPENDENCIES = ['doorbird']

_LOGGER = logging.getLogger(__name__)

SWITCHES = {
    "open_door": {
        "name": "Open Door",
        "icon": {
            True: "lock-open",
            False: "lock"
        },
        "time": datetime.timedelta(seconds=3)
    },
    "light_on": {
        "name": "Light On",
        "icon": {
            True: "lightbulb-on",
            False: "lightbulb"
        },
        "time": datetime.timedelta(minutes=5)
    }
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SWITCHES, default=[]):
        vol.All(cv.ensure_list([vol.In(SWITCHES)]))
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the DoorBird switch platform."""
    device = hass.data.get(DOORBIRD_DOMAIN)

    switches = []
    for switch in SWITCHES:
        _LOGGER.debug("Adding DoorBird switch %s", SWITCHES[switch]["name"])
        switches.append(DoorBirdSwitch(device, switch))

    add_devices(switches)
    _LOGGER.info("Added DoorBird switches")


class DoorBirdSwitch(SwitchDevice):
    """A relay in a DoorBird device."""

    def __init__(self, device, switch):
        """Initialize a relay in a DoorBird device."""
        self._device = device
        self._switch = switch
        self._state = False
        self._assume_off = datetime.datetime.min

    @property
    def name(self):
        """Return the name of the switch."""
        return SWITCHES[self._switch]["name"]

    @property
    def icon(self):
        """Return the icon to display."""
        return "mdi:{}".format(SWITCHES[self._switch]["icon"][self._state])

    @property
    def is_on(self):
        """Get the assumed state of the relay."""
        return self._state

    def turn_on(self, **kwargs):
        """Power the relay."""
        if self._switch == "open_door":
            self._state = self._device.open_door()
        elif self._switch == "light_on":
            self._state = self._device.turn_light_on()

        now = datetime.datetime.now()
        self._assume_off = now + SWITCHES[self._switch]["time"]

    def turn_off(self, **kwargs):
        """Turn off the relays is not needed. They are time-based."""
        raise NotImplementedError(
            "DoorBird relays cannot be manually turned off.")

    def update(self):
        """Wait for the correct amount of assumed time to pass."""
        if self._state and self._assume_off <= datetime.datetime.now():
            self._state = False
            self._assume_off = datetime.datetime.min
