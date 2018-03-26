"""
Support for Anthem Network Receivers and Processors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.anthemav/
"""
import logging
import asyncio

import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA, SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_SELECT_SOURCE,
    SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET, MediaPlayerDevice)
from homeassistant.const import (
    CONF_NAME, CONF_HOST, CONF_PORT, STATE_OFF, STATE_ON, STATE_UNKNOWN,
    EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['anthemav==1.1.8']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'anthemav'

DEFAULT_PORT = 14999

SUPPORT_ANTHEMAV = SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    })


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up our socket to the AVR."""
    import anthemav

    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    name = config.get(CONF_NAME)
    device = None

    _LOGGER.info("Provisioning Anthem AVR device at %s:%d", host, port)

    def async_anthemav_update_callback(message):
        """Receive notification from transport that new data exists."""
        _LOGGER.info("Received update callback from AVR: %s", message)
        hass.async_add_job(device.async_update_ha_state())

    avr = yield from anthemav.Connection.create(
        host=host, port=port, loop=hass.loop,
        update_callback=async_anthemav_update_callback)

    device = AnthemAVR(avr, name)

    _LOGGER.debug("dump_devicedata: %s", device.dump_avrdata)
    _LOGGER.debug("dump_conndata: %s", avr.dump_conndata)
    _LOGGER.debug("dump_rawdata: %s", avr.protocol.dump_rawdata)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, device.avr.close)
    async_add_devices([device])


class AnthemAVR(MediaPlayerDevice):
    """Entity reading values from Anthem AVR protocol."""

    def __init__(self, avr, name):
        """Initialize entity with transport."""
        super().__init__()
        self.avr = avr
        self._name = name

    def _lookup(self, propname, dval=None):
        return getattr(self.avr.protocol, propname, dval)

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_ANTHEMAV

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return name of device."""
        return self._name or self._lookup('model')

    @property
    def state(self):
        """Return state of power on/off."""
        pwrstate = self._lookup('power')

        if pwrstate is True:
            return STATE_ON
        elif pwrstate is False:
            return STATE_OFF
        return STATE_UNKNOWN

    @property
    def is_volume_muted(self):
        """Return boolean reflecting mute state on device."""
        return self._lookup('mute', False)

    @property
    def volume_level(self):
        """Return volume level from 0 to 1."""
        return self._lookup('volume_as_percentage', 0.0)

    @property
    def media_title(self):
        """Return current input name (closest we have to media title)."""
        return self._lookup('input_name', 'No Source')

    @property
    def app_name(self):
        """Return details about current video and audio stream."""
        return self._lookup('video_input_resolution_text', '') + ' ' \
            + self._lookup('audio_input_name', '')

    @property
    def source(self):
        """Return currently selected input."""
        return self._lookup('input_name', "Unknown")

    @property
    def source_list(self):
        """Return all active, configured inputs."""
        return self._lookup('input_list', ["Unknown"])

    @asyncio.coroutine
    def async_select_source(self, source):
        """Change AVR to the designated source (by name)."""
        self._update_avr('input_name', source)

    @asyncio.coroutine
    def async_turn_off(self):
        """Turn AVR power off."""
        self._update_avr('power', False)

    @asyncio.coroutine
    def async_turn_on(self):
        """Turn AVR power on."""
        self._update_avr('power', True)

    @asyncio.coroutine
    def async_set_volume_level(self, volume):
        """Set AVR volume (0 to 1)."""
        self._update_avr('volume_as_percentage', volume)

    @asyncio.coroutine
    def async_mute_volume(self, mute):
        """Engage AVR mute."""
        self._update_avr('mute', mute)

    def _update_avr(self, propname, value):
        """Update a property in the AVR."""
        _LOGGER.info(
            "Sending command to AVR: set %s to %s", propname, str(value))
        setattr(self.avr.protocol, propname, value)

    @property
    def dump_avrdata(self):
        """Return state of avr object for debugging forensics."""
        attrs = vars(self)
        return(
            'dump_avrdata: '
            + ', '.join('%s: %s' % item for item in attrs.items()))
