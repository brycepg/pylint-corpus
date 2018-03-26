"""
Support for interacting with Digital Ocean droplets.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/switch.digital_ocean/
"""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.components.digital_ocean import (
    CONF_DROPLETS, ATTR_CREATED_AT, ATTR_DROPLET_ID, ATTR_DROPLET_NAME,
    ATTR_FEATURES, ATTR_IPV4_ADDRESS, ATTR_IPV6_ADDRESS, ATTR_MEMORY,
    ATTR_REGION, ATTR_VCPUS, DATA_DIGITAL_OCEAN)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['digital_ocean']

DEFAULT_NAME = 'Droplet'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DROPLETS): vol.All(cv.ensure_list, [cv.string]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Digital Ocean droplet switch."""
    digital = hass.data.get(DATA_DIGITAL_OCEAN)
    if not digital:
        return False

    droplets = config.get(CONF_DROPLETS)

    dev = []
    for droplet in droplets:
        droplet_id = digital.get_droplet_id(droplet)
        if droplet_id is None:
            _LOGGER.error("Droplet %s is not available", droplet)
            return False
        dev.append(DigitalOceanSwitch(digital, droplet_id))

    add_devices(dev, True)


class DigitalOceanSwitch(SwitchDevice):
    """Representation of a Digital Ocean droplet switch."""

    def __init__(self, do, droplet_id):
        """Initialize a new Digital Ocean sensor."""
        self._digital_ocean = do
        self._droplet_id = droplet_id
        self.data = None
        self._state = None

    @property
    def name(self):
        """Return the name of the switch."""
        return self.data.name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.data.status == 'active'

    @property
    def device_state_attributes(self):
        """Return the state attributes of the Digital Ocean droplet."""
        return {
            ATTR_CREATED_AT: self.data.created_at,
            ATTR_DROPLET_ID: self.data.id,
            ATTR_DROPLET_NAME: self.data.name,
            ATTR_FEATURES: self.data.features,
            ATTR_IPV4_ADDRESS: self.data.ip_address,
            ATTR_IPV6_ADDRESS: self.data.ip_v6_address,
            ATTR_MEMORY: self.data.memory,
            ATTR_REGION: self.data.region['name'],
            ATTR_VCPUS: self.data.vcpus,
        }

    def turn_on(self, **kwargs):
        """Boot-up the droplet."""
        if self.data.status != 'active':
            self.data.power_on()

    def turn_off(self, **kwargs):
        """Shutdown the droplet."""
        if self.data.status == 'active':
            self.data.power_off()

    def update(self):
        """Get the latest data from the device and update the data."""
        self._digital_ocean.update()

        for droplet in self._digital_ocean.data:
            if droplet.id == self._droplet_id:
                self.data = droplet
