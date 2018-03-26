"""
Support for Xiaomi Yeelight Wifi color bulb.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.yeelight/
"""
import logging
import colorsys
from typing import Tuple

import voluptuous as vol

from homeassistant.util.color import (
    color_temperature_mired_to_kelvin as mired_to_kelvin,
    color_temperature_kelvin_to_mired as kelvin_to_mired,
    color_temperature_to_rgb,
    color_RGB_to_xy,
    color_xy_brightness_to_RGB)
from homeassistant.const import CONF_DEVICES, CONF_NAME
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_TRANSITION, ATTR_COLOR_TEMP,
    ATTR_FLASH, ATTR_XY_COLOR, FLASH_SHORT, FLASH_LONG, ATTR_EFFECT,
    SUPPORT_BRIGHTNESS, SUPPORT_RGB_COLOR, SUPPORT_XY_COLOR,
    SUPPORT_TRANSITION,
    SUPPORT_COLOR_TEMP, SUPPORT_FLASH, SUPPORT_EFFECT,
    Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['yeelight==0.4.0']

_LOGGER = logging.getLogger(__name__)

CONF_TRANSITION = 'transition'
DEFAULT_TRANSITION = 350

CONF_SAVE_ON_CHANGE = 'save_on_change'
CONF_MODE_MUSIC = 'use_music_mode'

DOMAIN = 'yeelight'

DEVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_TRANSITION, default=DEFAULT_TRANSITION): cv.positive_int,
    vol.Optional(CONF_MODE_MUSIC, default=False): cv.boolean,
    vol.Optional(CONF_SAVE_ON_CHANGE, default=True): cv.boolean,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA}, })

SUPPORT_YEELIGHT = (SUPPORT_BRIGHTNESS |
                    SUPPORT_TRANSITION |
                    SUPPORT_FLASH)

SUPPORT_YEELIGHT_RGB = (SUPPORT_YEELIGHT |
                        SUPPORT_RGB_COLOR |
                        SUPPORT_XY_COLOR |
                        SUPPORT_EFFECT |
                        SUPPORT_COLOR_TEMP)

YEELIGHT_MIN_KELVIN = YEELIGHT_MAX_KELVIN = 2700
YEELIGHT_RGB_MIN_KELVIN = 1700
YEELIGHT_RGB_MAX_KELVIN = 6500

EFFECT_DISCO = "Disco"
EFFECT_TEMP = "Slow Temp"
EFFECT_STROBE = "Strobe epilepsy!"
EFFECT_STROBE_COLOR = "Strobe color"
EFFECT_ALARM = "Alarm"
EFFECT_POLICE = "Police"
EFFECT_POLICE2 = "Police2"
EFFECT_CHRISTMAS = "Christmas"
EFFECT_RGB = "RGB"
EFFECT_RANDOM_LOOP = "Random Loop"
EFFECT_FAST_RANDOM_LOOP = "Fast Random Loop"
EFFECT_SLOWDOWN = "Slowdown"
EFFECT_WHATSAPP = "WhatsApp"
EFFECT_FACEBOOK = "Facebook"
EFFECT_TWITTER = "Twitter"
EFFECT_STOP = "Stop"

YEELIGHT_EFFECT_LIST = [
    EFFECT_DISCO,
    EFFECT_TEMP,
    EFFECT_STROBE,
    EFFECT_STROBE_COLOR,
    EFFECT_ALARM,
    EFFECT_POLICE,
    EFFECT_POLICE2,
    EFFECT_CHRISTMAS,
    EFFECT_RGB,
    EFFECT_RANDOM_LOOP,
    EFFECT_FAST_RANDOM_LOOP,
    EFFECT_SLOWDOWN,
    EFFECT_WHATSAPP,
    EFFECT_FACEBOOK,
    EFFECT_TWITTER,
    EFFECT_STOP]


# Travis-CI runs too old astroid https://github.com/PyCQA/pylint/issues/1212
# pylint: disable=invalid-sequence-index
def hsv_to_rgb(hsv: Tuple[float, float, float]) -> Tuple[int, int, int]:
    """Convert HSV tuple (degrees, %, %) to RGB (values 0-255)."""
    red, green, blue = colorsys.hsv_to_rgb(hsv[0]/360, hsv[1]/100, hsv[2]/100)
    return int(red * 255), int(green * 255), int(blue * 255)


def _cmd(func):
    """Define a wrapper to catch exceptions from the bulb."""
    def _wrap(self, *args, **kwargs):
        import yeelight
        try:
            _LOGGER.debug("Calling %s with %s %s", func, args, kwargs)
            return func(self, *args, **kwargs)
        except yeelight.BulbException as ex:
            _LOGGER.error("Error when calling %s: %s", func, ex)

    return _wrap


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Yeelight bulbs."""
    lights = []
    if discovery_info is not None:
        _LOGGER.debug("Adding autodetected %s", discovery_info['hostname'])

        # Not using hostname, as it seems to vary.
        name = "yeelight_%s_%s" % (discovery_info['device_type'],
                                   discovery_info['properties']['mac'])
        device = {'name': name, 'ipaddr': discovery_info['host']}

        lights.append(YeelightLight(device, DEVICE_SCHEMA({})))
    else:
        for ipaddr, device_config in config[CONF_DEVICES].items():
            _LOGGER.debug("Adding configured %s", device_config[CONF_NAME])

            device = {'name': device_config[CONF_NAME], 'ipaddr': ipaddr}
            lights.append(YeelightLight(device, device_config))

    add_devices(lights, True)


class YeelightLight(Light):
    """Representation of a Yeelight light."""

    def __init__(self, device, config):
        """Initialize the Yeelight light."""
        self.config = config
        self._name = device['name']
        self._ipaddr = device['ipaddr']

        self._supported_features = SUPPORT_YEELIGHT
        self._available = False
        self._bulb_device = None

        self._brightness = None
        self._color_temp = None
        self._is_on = None
        self._rgb = None
        self._xy = None

    @property
    def available(self) -> bool:
        """Return if bulb is available."""
        return self._available

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return YEELIGHT_EFFECT_LIST

    @property
    def color_temp(self) -> int:
        """Return the color temperature."""
        return self._color_temp

    @property
    def name(self) -> str:
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 1..255."""
        return self._brightness

    @property
    def min_mireds(self):
        """Return minimum supported color temperature."""
        if self.supported_features & SUPPORT_COLOR_TEMP:
            return kelvin_to_mired(YEELIGHT_RGB_MAX_KELVIN)
        return kelvin_to_mired(YEELIGHT_MAX_KELVIN)

    @property
    def max_mireds(self):
        """Return maximum supported color temperature."""
        if self.supported_features & SUPPORT_COLOR_TEMP:
            return kelvin_to_mired(YEELIGHT_RGB_MIN_KELVIN)
        return kelvin_to_mired(YEELIGHT_MIN_KELVIN)

    def _get_rgb_from_properties(self):
        rgb = self._properties.get('rgb', None)
        color_mode = self._properties.get('color_mode', None)
        if not rgb or not color_mode:
            return rgb

        color_mode = int(color_mode)
        if color_mode == 2:  # color temperature
            temp_in_k = mired_to_kelvin(self._color_temp)
            return color_temperature_to_rgb(temp_in_k)
        if color_mode == 3:  # hsv
            hue = int(self._properties.get('hue'))
            sat = int(self._properties.get('sat'))
            val = int(self._properties.get('bright'))
            return hsv_to_rgb((hue, sat, val))

        rgb = int(rgb)
        blue = rgb & 0xff
        green = (rgb >> 8) & 0xff
        red = (rgb >> 16) & 0xff

        return red, green, blue

    @property
    def rgb_color(self) -> tuple:
        """Return the color property."""
        return self._rgb

    @property
    def xy_color(self) -> tuple:
        """Return the XY color value."""
        return self._xy

    @property
    def _properties(self) -> dict:
        return self._bulb.last_properties

    @property
    def _bulb(self) -> 'yeelight.Bulb':
        import yeelight
        if self._bulb_device is None:
            try:
                self._bulb_device = yeelight.Bulb(self._ipaddr)
                self._bulb_device.get_properties()  # force init for type

                self._available = True
            except yeelight.BulbException as ex:
                self._available = False
                _LOGGER.error("Failed to connect to bulb %s, %s: %s",
                              self._ipaddr, self._name, ex)

        return self._bulb_device

    def set_music_mode(self, mode) -> None:
        """Set the music mode on or off."""
        if mode:
            self._bulb.start_music()
        else:
            self._bulb.stop_music()

    def update(self) -> None:
        """Update properties from the bulb."""
        import yeelight
        try:
            self._bulb.get_properties()

            if self._bulb_device.bulb_type == yeelight.BulbType.Color:
                self._supported_features = SUPPORT_YEELIGHT_RGB

            self._is_on = self._properties.get('power') == 'on'

            bright = self._properties.get('bright', None)
            if bright:
                self._brightness = 255 * (int(bright) / 100)

            temp_in_k = self._properties.get('ct', None)
            if temp_in_k:
                self._color_temp = kelvin_to_mired(int(temp_in_k))

            self._rgb = self._get_rgb_from_properties()

            if self._rgb:
                xyb = color_RGB_to_xy(*self._rgb)
                self._xy = (xyb[0], xyb[1])
            else:
                self._xy = None

            self._available = True
        except yeelight.BulbException as ex:
            if self._available:  # just inform once
                _LOGGER.error("Unable to update bulb status: %s", ex)
            self._available = False

    @_cmd
    def set_brightness(self, brightness, duration) -> None:
        """Set bulb brightness."""
        if brightness:
            _LOGGER.debug("Setting brightness: %s", brightness)
            self._bulb.set_brightness(brightness / 255 * 100,
                                      duration=duration)

    @_cmd
    def set_rgb(self, rgb, duration) -> None:
        """Set bulb's color."""
        if rgb and self.supported_features & SUPPORT_RGB_COLOR:
            _LOGGER.debug("Setting RGB: %s", rgb)
            self._bulb.set_rgb(rgb[0], rgb[1], rgb[2], duration=duration)

    @_cmd
    def set_colortemp(self, colortemp, duration) -> None:
        """Set bulb's color temperature."""
        if colortemp and self.supported_features & SUPPORT_COLOR_TEMP:
            temp_in_k = mired_to_kelvin(colortemp)
            _LOGGER.debug("Setting color temp: %s K", temp_in_k)

            self._bulb.set_color_temp(temp_in_k, duration=duration)

    @_cmd
    def set_default(self) -> None:
        """Set current options as default."""
        self._bulb.set_default()

    @_cmd
    def set_flash(self, flash) -> None:
        """Activate flash."""
        if flash:
            from yeelight import (RGBTransition, SleepTransition, Flow,
                                  BulbException)
            if self._bulb.last_properties["color_mode"] != 1:
                _LOGGER.error("Flash supported currently only in RGB mode.")
                return

            transition = int(self.config[CONF_TRANSITION])
            if flash == FLASH_LONG:
                count = 1
                duration = transition * 5
            if flash == FLASH_SHORT:
                count = 1
                duration = transition * 2

            red, green, blue = self.rgb_color

            transitions = list()
            transitions.append(
                RGBTransition(255, 0, 0, brightness=10, duration=duration))
            transitions.append(SleepTransition(
                duration=transition))
            transitions.append(
                RGBTransition(red, green, blue, brightness=self.brightness,
                              duration=duration))

            flow = Flow(count=count, transitions=transitions)
            try:
                self._bulb.start_flow(flow)
            except BulbException as ex:
                _LOGGER.error("Unable to set flash: %s", ex)

    @_cmd
    def set_effect(self, effect) -> None:
        """Activate effect."""
        if effect:
            from yeelight import (Flow, BulbException)
            from yeelight.transitions import (disco, temp, strobe, pulse,
                                              strobe_color, alarm, police,
                                              police2, christmas, rgb,
                                              randomloop, slowdown)
            if effect == EFFECT_STOP:
                self._bulb.stop_flow()
                return
            if effect == EFFECT_DISCO:
                flow = Flow(count=0, transitions=disco())
            if effect == EFFECT_TEMP:
                flow = Flow(count=0, transitions=temp())
            if effect == EFFECT_STROBE:
                flow = Flow(count=0, transitions=strobe())
            if effect == EFFECT_STROBE_COLOR:
                flow = Flow(count=0, transitions=strobe_color())
            if effect == EFFECT_ALARM:
                flow = Flow(count=0, transitions=alarm())
            if effect == EFFECT_POLICE:
                flow = Flow(count=0, transitions=police())
            if effect == EFFECT_POLICE2:
                flow = Flow(count=0, transitions=police2())
            if effect == EFFECT_CHRISTMAS:
                flow = Flow(count=0, transitions=christmas())
            if effect == EFFECT_RGB:
                flow = Flow(count=0, transitions=rgb())
            if effect == EFFECT_RANDOM_LOOP:
                flow = Flow(count=0, transitions=randomloop())
            if effect == EFFECT_FAST_RANDOM_LOOP:
                flow = Flow(count=0, transitions=randomloop(duration=250))
            if effect == EFFECT_SLOWDOWN:
                flow = Flow(count=0, transitions=slowdown())
            if effect == EFFECT_WHATSAPP:
                flow = Flow(count=2, transitions=pulse(37, 211, 102))
            if effect == EFFECT_FACEBOOK:
                flow = Flow(count=2, transitions=pulse(59, 89, 152))
            if effect == EFFECT_TWITTER:
                flow = Flow(count=2, transitions=pulse(0, 172, 237))

            try:
                self._bulb.start_flow(flow)
            except BulbException as ex:
                _LOGGER.error("Unable to set effect: %s", ex)

    def turn_on(self, **kwargs) -> None:
        """Turn the bulb on."""
        import yeelight
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        colortemp = kwargs.get(ATTR_COLOR_TEMP)
        rgb = kwargs.get(ATTR_RGB_COLOR)
        flash = kwargs.get(ATTR_FLASH)
        effect = kwargs.get(ATTR_EFFECT)
        xy_color = kwargs.get(ATTR_XY_COLOR)

        duration = int(self.config[CONF_TRANSITION])  # in ms
        if ATTR_TRANSITION in kwargs:  # passed kwarg overrides config
            duration = int(kwargs.get(ATTR_TRANSITION) * 1000)  # kwarg in s

        try:
            self._bulb.turn_on(duration=duration)
        except yeelight.BulbException as ex:
            _LOGGER.error("Unable to turn the bulb on: %s", ex)
            return

        if self.config[CONF_MODE_MUSIC] and not self._bulb.music_mode:
            try:
                self.set_music_mode(self.config[CONF_MODE_MUSIC])
            except yeelight.BulbException as ex:
                _LOGGER.error("Unable to turn on music mode,"
                              "consider disabling it: %s", ex)
        if xy_color and brightness:
            rgb = color_xy_brightness_to_RGB(xy_color[0], xy_color[1],
                                             brightness)

        try:
            # values checked for none in methods
            self.set_rgb(rgb, duration)
            self.set_colortemp(colortemp, duration)
            self.set_brightness(brightness, duration)
            self.set_flash(flash)
            self.set_effect(effect)
        except yeelight.BulbException as ex:
            _LOGGER.error("Unable to set bulb properties: %s", ex)
            return

        # save the current state if we had a manual change.
        if self.config[CONF_SAVE_ON_CHANGE] and (brightness
                                                 or colortemp
                                                 or rgb):
            try:
                self.set_default()
            except yeelight.BulbException as ex:
                _LOGGER.error("Unable to set the defaults: %s", ex)
                return

    def turn_off(self, **kwargs) -> None:
        """Turn off."""
        import yeelight
        duration = int(self.config[CONF_TRANSITION])  # in ms
        if ATTR_TRANSITION in kwargs:  # passed kwarg overrides config
            duration = int(kwargs.get(ATTR_TRANSITION) * 1000)  # kwarg in s
        try:
            self._bulb.turn_off(duration=duration)
        except yeelight.BulbException as ex:
            _LOGGER.error("Unable to turn the bulb off: %s", ex)
