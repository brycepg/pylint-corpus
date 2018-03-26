"""
Binary sensors on Zigbee Home Automation networks.

For more details on this platform, please refer to the documentation
at https://home-assistant.io/components/binary_sensor.zha/
"""
import logging

from homeassistant.components.binary_sensor import DOMAIN, BinarySensorDevice
from homeassistant.components import zha

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['zha']

# ZigBee Cluster Library Zone Type to Home Assistant device class
CLASS_MAPPING = {
    0x000d: 'motion',
    0x0015: 'opening',
    0x0028: 'smoke',
    0x002a: 'moisture',
    0x002b: 'gas',
    0x002d: 'vibration',
}


async def async_setup_platform(hass, config, async_add_devices,
                               discovery_info=None):
    """Set up the Zigbee Home Automation binary sensors."""
    discovery_info = zha.get_discovery_info(hass, discovery_info)
    if discovery_info is None:
        return

    from zigpy.zcl.clusters.security import IasZone

    in_clusters = discovery_info['in_clusters']

    device_class = None
    cluster = in_clusters[IasZone.cluster_id]
    if discovery_info['new_join']:
        await cluster.bind()
        ieee = cluster.endpoint.device.application.ieee
        await cluster.write_attributes({'cie_addr': ieee})

    try:
        zone_type = await cluster['zone_type']
        device_class = CLASS_MAPPING.get(zone_type, None)
    except Exception:  # pylint: disable=broad-except
        # If we fail to read from the device, use a non-specific class
        pass

    sensor = BinarySensor(device_class, **discovery_info)
    async_add_devices([sensor], update_before_add=True)


class BinarySensor(zha.Entity, BinarySensorDevice):
    """THe ZHA Binary Sensor."""

    _domain = DOMAIN

    def __init__(self, device_class, **kwargs):
        """Initialize the ZHA binary sensor."""
        super().__init__(**kwargs)
        self._device_class = device_class
        from zigpy.zcl.clusters.security import IasZone
        self._ias_zone_cluster = self._in_clusters[IasZone.cluster_id]

    @property
    def should_poll(self) -> bool:
        """Let zha handle polling."""
        return False

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        if self._state == 'unknown':
            return False
        return bool(self._state)

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    def cluster_command(self, tsn, command_id, args):
        """Handle commands received to this cluster."""
        if command_id == 0:
            self._state = args[0] & 3
            _LOGGER.debug("Updated alarm state: %s", self._state)
            self.async_schedule_update_ha_state()
        elif command_id == 1:
            _LOGGER.debug("Enroll requested")
            res = self._ias_zone_cluster.enroll_response(0, 0)
            self.hass.async_add_job(res)

    async def async_update(self):
        """Retrieve latest state."""
        from bellows.types.basic import uint16_t

        result = await zha.safe_read(self._endpoint.ias_zone,
                                     ['zone_status'])
        state = result.get('zone_status', self._state)
        if isinstance(state, (int, uint16_t)):
            self._state = result.get('zone_status', self._state) & 3
