"""
Support for IP Webcam settings.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.android_ip_webcam/
"""
import asyncio

from homeassistant.components.switch import SwitchDevice
from homeassistant.components.android_ip_webcam import (
    KEY_MAP, ICON_MAP, DATA_IP_WEBCAM, AndroidIPCamEntity, CONF_HOST,
    CONF_NAME, CONF_SWITCHES)

DEPENDENCIES = ['android_ip_webcam']


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the IP Webcam switch platform."""
    if discovery_info is None:
        return

    host = discovery_info[CONF_HOST]
    name = discovery_info[CONF_NAME]
    switches = discovery_info[CONF_SWITCHES]
    ipcam = hass.data[DATA_IP_WEBCAM][host]

    all_switches = []

    for setting in switches:
        all_switches.append(IPWebcamSettingsSwitch(name, host, ipcam, setting))

    async_add_devices(all_switches, True)


class IPWebcamSettingsSwitch(AndroidIPCamEntity, SwitchDevice):
    """An abstract class for an IP Webcam setting."""

    def __init__(self, name, host, ipcam, setting):
        """Initialize the settings switch."""
        super().__init__(host, ipcam)

        self._setting = setting
        self._mapped_name = KEY_MAP.get(self._setting, self._setting)
        self._name = '{} {}'.format(name, self._mapped_name)
        self._state = False

    @property
    def name(self):
        """Return the name of the node."""
        return self._name

    @asyncio.coroutine
    def async_update(self):
        """Get the updated status of the switch."""
        self._state = bool(self._ipcam.current_settings.get(self._setting))

    @property
    def is_on(self):
        """Return the boolean response if the node is on."""
        return self._state

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Turn device on."""
        if self._setting == 'torch':
            yield from self._ipcam.torch(activate=True)
        elif self._setting == 'focus':
            yield from self._ipcam.focus(activate=True)
        elif self._setting == 'video_recording':
            yield from self._ipcam.record(record=True)
        else:
            yield from self._ipcam.change_setting(self._setting, True)
        self._state = True
        self.async_schedule_update_ha_state()

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """Turn device off."""
        if self._setting == 'torch':
            yield from self._ipcam.torch(activate=False)
        elif self._setting == 'focus':
            yield from self._ipcam.focus(activate=False)
        elif self._setting == 'video_recording':
            yield from self._ipcam.record(record=False)
        else:
            yield from self._ipcam.change_setting(self._setting, False)
        self._state = False
        self.async_schedule_update_ha_state()

    @property
    def icon(self):
        """Return the icon for the switch."""
        return ICON_MAP.get(self._setting, 'mdi:flash')
