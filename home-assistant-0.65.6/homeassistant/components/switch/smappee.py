"""
Support for interacting with Smappee Comport Plugs.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/switch.smappee/
"""
import logging

from homeassistant.components.smappee import DATA_SMAPPEE
from homeassistant.components.switch import (SwitchDevice)

DEPENDENCIES = ['smappee']

_LOGGER = logging.getLogger(__name__)

ICON = 'mdi:power-plug'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Smappee Comfort Plugs."""
    smappee = hass.data[DATA_SMAPPEE]

    dev = []
    if smappee.is_remote_active:
        for location_id in smappee.locations.keys():
            for items in smappee.info[location_id].get('actuators'):
                if items.get('name') != '':
                    _LOGGER.debug("Remote actuator %s", items)
                    dev.append(SmappeeSwitch(smappee,
                                             items.get('name'),
                                             location_id,
                                             items.get('id')))
    elif smappee.is_local_active:
        for items in smappee.local_devices:
            _LOGGER.debug("Local actuator %s", items)
            dev.append(SmappeeSwitch(smappee,
                                     items.get('value'),
                                     None,
                                     items.get('key')))
    add_devices(dev)


class SmappeeSwitch(SwitchDevice):
    """Representation of a Smappee Comport Plug."""

    def __init__(self, smappee, name, location_id, switch_id):
        """Initialize a new Smappee Comfort Plug."""
        self._name = name
        self._state = False
        self._smappee = smappee
        self._location_id = location_id
        self._switch_id = switch_id
        self._remoteswitch = True
        if location_id is None:
            self._remoteswitch = False

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return ICON

    def turn_on(self, **kwargs):
        """Turn on Comport Plug."""
        if self._smappee.actuator_on(self._location_id, self._switch_id,
                                     self._remoteswitch):
            self._state = True

    def turn_off(self, **kwargs):
        """Turn off Comport Plug."""
        if self._smappee.actuator_off(self._location_id, self._switch_id,
                                      self._remoteswitch):
            self._state = False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        if self._remoteswitch:
            attr['Location Id'] = self._location_id
            attr['Location Name'] = self._smappee.locations[self._location_id]
        attr['Switch Id'] = self._switch_id
        return attr
