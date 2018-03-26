"""
Support for Yeelight Sunflower color bulbs (not Yeelight Blue or WiFi).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.yeelightsunflower/
"""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    Light, ATTR_RGB_COLOR, SUPPORT_RGB_COLOR, ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS, PLATFORM_SCHEMA)
from homeassistant.const import CONF_HOST

REQUIREMENTS = ['yeelightsunflower==0.0.8']

_LOGGER = logging.getLogger(__name__)

SUPPORT_YEELIGHT_SUNFLOWER = (SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Yeelight Sunflower Light platform."""
    import yeelightsunflower

    host = config.get(CONF_HOST)
    hub = yeelightsunflower.Hub(host)

    if not hub.available:
        _LOGGER.error("Could not connect to Yeelight Sunflower hub")
        return False

    add_devices(SunflowerBulb(light) for light in hub.get_lights())


class SunflowerBulb(Light):
    """Representation of a Yeelight Sunflower Light."""

    def __init__(self, light):
        """Initialize a Yeelight Sunflower bulb."""
        self._light = light
        self._available = light.available
        self._brightness = light.brightness
        self._is_on = light.is_on
        self._rgb_color = light.rgb_color

    @property
    def name(self):
        """Return the display name of this light."""
        return 'sunflower_{}'.format(self._light.zid)

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._is_on

    @property
    def brightness(self):
        """Return the brightness is 0-255; Yeelight's brightness is 0-100."""
        return int(self._brightness / 100 * 255)

    @property
    def rgb_color(self):
        """Return the color property."""
        return self._rgb_color

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_YEELIGHT_SUNFLOWER

    def turn_on(self, **kwargs):
        """Instruct the light to turn on, optionally set colour/brightness."""
        # when no arguments, just turn light on (full brightness)
        if not kwargs:
            self._light.turn_on()
        else:
            if ATTR_RGB_COLOR in kwargs and ATTR_BRIGHTNESS in kwargs:
                rgb = kwargs[ATTR_RGB_COLOR]
                bright = int(kwargs[ATTR_BRIGHTNESS] / 255 * 100)
                self._light.set_all(rgb[0], rgb[1], rgb[2], bright)
            elif ATTR_RGB_COLOR in kwargs:
                rgb = kwargs[ATTR_RGB_COLOR]
                self._light.set_rgb_color(rgb[0], rgb[1], rgb[2])
            elif ATTR_BRIGHTNESS in kwargs:
                bright = int(kwargs[ATTR_BRIGHTNESS] / 255 * 100)
                self._light.set_brightness(bright)

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._light.turn_off()

    def update(self):
        """Fetch new state data for this light and update local values."""
        self._light.update()
        self._available = self._light.available
        self._brightness = self._light.brightness
        self._is_on = self._light.is_on
        self._rgb_color = self._light.rgb_color
