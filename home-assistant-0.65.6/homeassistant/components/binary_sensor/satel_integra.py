"""
Support for Satel Integra zone states- represented as binary sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.satel_integra/
"""
import asyncio
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.satel_integra import (CONF_ZONES,
                                                    CONF_ZONE_NAME,
                                                    CONF_ZONE_TYPE,
                                                    SIGNAL_ZONES_UPDATED)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

DEPENDENCIES = ['satel_integra']

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Satel Integra binary sensor devices."""
    if not discovery_info:
        return

    configured_zones = discovery_info[CONF_ZONES]

    devices = []

    for zone_num, device_config_data in configured_zones.items():
        zone_type = device_config_data[CONF_ZONE_TYPE]
        zone_name = device_config_data[CONF_ZONE_NAME]
        device = SatelIntegraBinarySensor(zone_num, zone_name, zone_type)
        devices.append(device)

    async_add_devices(devices)


class SatelIntegraBinarySensor(BinarySensorDevice):
    """Representation of an Satel Integra binary sensor."""

    def __init__(self, zone_number, zone_name, zone_type):
        """Initialize the binary_sensor."""
        self._zone_number = zone_number
        self._name = zone_name
        self._zone_type = zone_type
        self._state = 0

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(
            self.hass, SIGNAL_ZONES_UPDATED, self._zones_updated)

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self):
        """Icon for device by its type."""
        if self._zone_type == 'smoke':
            return "mdi:fire"

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state == 1

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return self._zone_type

    @callback
    def _zones_updated(self, zones):
        """Update the zone's state, if needed."""
        if self._zone_number in zones \
                and self._state != zones[self._zone_number]:
            self._state = zones[self._zone_number]
            self.async_schedule_update_ha_state()
