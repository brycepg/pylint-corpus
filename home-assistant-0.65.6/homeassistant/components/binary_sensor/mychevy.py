"""Support for MyChevy sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.mychevy/
"""

import asyncio
import logging

from homeassistant.components.mychevy import (
    EVBinarySensorConfig, DOMAIN as MYCHEVY_DOMAIN, UPDATE_TOPIC
)
from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT, BinarySensorDevice)
from homeassistant.core import callback
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

SENSORS = [
    EVBinarySensorConfig("Plugged In", "plugged_in", "plug")
]


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the MyChevy sensors."""
    if discovery_info is None:
        return

    sensors = []
    hub = hass.data[MYCHEVY_DOMAIN]
    for sconfig in SENSORS:
        sensors.append(EVBinarySensor(hub, sconfig))

    async_add_devices(sensors)


class EVBinarySensor(BinarySensorDevice):
    """Base EVSensor class.

    The only real difference between sensors is which units and what
    attribute from the car object they are returning. All logic can be
    built with just setting subclass attributes.

    """

    def __init__(self, connection, config):
        """Initialize sensor with car connection."""
        self._conn = connection
        self._name = config.name
        self._attr = config.attr
        self._type = config.device_class
        self._is_on = None

        self.entity_id = ENTITY_ID_FORMAT.format(
            '{}_{}'.format(MYCHEVY_DOMAIN, slugify(self._name)))

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def is_on(self):
        """Return if on."""
        return self._is_on

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        self.hass.helpers.dispatcher.async_dispatcher_connect(
            UPDATE_TOPIC, self.async_update_callback)

    @callback
    def async_update_callback(self):
        """Update state."""
        if self._conn.car is not None:
            self._is_on = getattr(self._conn.car, self._attr, None)
            self.async_schedule_update_ha_state()

    @property
    def should_poll(self):
        """Return the polling state."""
        return False
