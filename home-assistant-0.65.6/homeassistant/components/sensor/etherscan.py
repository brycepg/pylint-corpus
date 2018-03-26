"""
Support for Etherscan sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.etherscan/
"""
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['python-etherscan-api==0.0.3']

CONF_ADDRESS = 'address'
CONF_TOKEN = 'token'
CONF_TOKEN_ADDRESS = 'token_address'
CONF_ATTRIBUTION = "Data provided by etherscan.io"

SCAN_INTERVAL = timedelta(minutes=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_TOKEN): cv.string,
    vol.Optional(CONF_TOKEN_ADDRESS): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Etherscan.io sensors."""
    address = config.get(CONF_ADDRESS)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    token_address = config.get(CONF_TOKEN_ADDRESS)

    if token:
        token = token.upper()
        if not name:
            name = "%s Balance" % token
    if not name:
        name = "ETH Balance"

    add_devices([EtherscanSensor(name, address, token, token_address)], True)


class EtherscanSensor(Entity):
    """Representation of an Etherscan.io sensor."""

    def __init__(self, name, address, token, token_address):
        """Initialize the sensor."""
        self._name = name
        self._address = address
        self._token_address = token_address
        self._token = token
        self._state = None
        self._unit_of_measurement = self._token or "ETH"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
        }

    def update(self):
        """Get the latest state of the sensor."""
        from pyetherscan import get_balance
        if self._token_address:
            self._state = get_balance(self._address, self._token_address)
        elif self._token:
            self._state = get_balance(self._address, self._token)
        else:
            self._state = get_balance(self._address)
