"""
Support for Xiaomi Philips Lights (LED Ball & Ceiling Lamp, Eyecare Lamp 2).

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/light.xiaomi_miio/
"""
import asyncio
from functools import partial
import logging
from math import ceil
from datetime import timedelta
import datetime

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    PLATFORM_SCHEMA, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS,
    ATTR_COLOR_TEMP, SUPPORT_COLOR_TEMP, Light, ATTR_ENTITY_ID, DOMAIN, )

from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TOKEN, )
from homeassistant.exceptions import PlatformNotReady
from homeassistant.util import dt

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Xiaomi Philips Light'
DATA_KEY = 'light.xiaomi_miio'

CONF_MODEL = 'model'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MODEL): vol.In(
        ['philips.light.sread1',
         'philips.light.ceiling',
         'philips.light.zyceiling',
         'philips.light.bulb']),
})

REQUIREMENTS = ['python-miio==0.3.7']

# The light does not accept cct values < 1
CCT_MIN = 1
CCT_MAX = 100

DELAYED_TURN_OFF_MAX_DEVIATION = 4

SUCCESS = ['ok']
ATTR_MODEL = 'model'
ATTR_SCENE = 'scene'
ATTR_DELAYED_TURN_OFF = 'delayed_turn_off'
ATTR_TIME_PERIOD = 'time_period'

SERVICE_SET_SCENE = 'xiaomi_miio_set_scene'
SERVICE_SET_DELAYED_TURN_OFF = 'xiaomi_miio_set_delayed_turn_off'

XIAOMI_MIIO_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
})

SERVICE_SCHEMA_SET_SCENE = XIAOMI_MIIO_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_SCENE):
        vol.All(vol.Coerce(int), vol.Clamp(min=1, max=4))
})

SERVICE_SCHEMA_SET_DELAYED_TURN_OFF = XIAOMI_MIIO_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_TIME_PERIOD):
        vol.All(cv.time_period, cv.positive_timedelta)
})

SERVICE_TO_METHOD = {
    SERVICE_SET_DELAYED_TURN_OFF: {
        'method': 'async_set_delayed_turn_off',
        'schema': SERVICE_SCHEMA_SET_DELAYED_TURN_OFF},
    SERVICE_SET_SCENE: {
        'method': 'async_set_scene',
        'schema': SERVICE_SCHEMA_SET_SCENE},
}


# pylint: disable=unused-argument
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the light from config."""
    from miio import Device, DeviceException
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    model = config.get(CONF_MODEL)

    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])

    if model is None:
        try:
            miio_device = Device(host, token)
            device_info = miio_device.info()
            model = device_info.model
            _LOGGER.info("%s %s %s detected",
                         model,
                         device_info.firmware_version,
                         device_info.hardware_version)
        except DeviceException:
            raise PlatformNotReady

    if model == 'philips.light.sread1':
        from miio import PhilipsEyecare
        light = PhilipsEyecare(host, token)
        device = XiaomiPhilipsEyecareLamp(name, light, model)
    elif model in ['philips.light.ceiling', 'philips.light.zyceiling']:
        from miio import Ceil
        light = Ceil(host, token)
        device = XiaomiPhilipsCeilingLamp(name, light, model)
    elif model == 'philips.light.bulb':
        from miio import PhilipsBulb
        light = PhilipsBulb(host, token)
        device = XiaomiPhilipsLightBall(name, light, model)
    else:
        _LOGGER.error(
            'Unsupported device found! Please create an issue at '
            'https://github.com/rytilahti/python-miio/issues '
            'and provide the following data: %s', model)
        return False

    hass.data[DATA_KEY][host] = device
    async_add_devices([device], update_before_add=True)

    @asyncio.coroutine
    def async_service_handler(service):
        """Map services to methods on Xiaomi Philips Lights."""
        method = SERVICE_TO_METHOD.get(service.service)
        params = {key: value for key, value in service.data.items()
                  if key != ATTR_ENTITY_ID}
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        if entity_ids:
            target_devices = [dev for dev in hass.data[DATA_KEY].values()
                              if dev.entity_id in entity_ids]
        else:
            target_devices = hass.data[DATA_KEY].values()

        update_tasks = []
        for target_device in target_devices:
            yield from getattr(target_device, method['method'])(**params)
            update_tasks.append(target_device.async_update_ha_state(True))

        if update_tasks:
            yield from asyncio.wait(update_tasks, loop=hass.loop)

    for xiaomi_miio_service in SERVICE_TO_METHOD:
        schema = SERVICE_TO_METHOD[xiaomi_miio_service].get(
            'schema', XIAOMI_MIIO_SERVICE_SCHEMA)
        hass.services.async_register(
            DOMAIN, xiaomi_miio_service, async_service_handler, schema=schema)


class XiaomiPhilipsGenericLight(Light):
    """Representation of a Xiaomi Philips Light."""

    def __init__(self, name, light, model):
        """Initialize the light device."""
        self._name = name
        self._model = model

        self._brightness = None
        self._color_temp = None

        self._light = light
        self._state = None
        self._state_attrs = {
            ATTR_MODEL: self._model,
            ATTR_SCENE: None,
            ATTR_DELAYED_TURN_OFF: None,
        }

    @property
    def should_poll(self):
        """Poll the light."""
        return True

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def available(self):
        """Return true when state is known."""
        return self._state is not None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def supported_features(self):
        """Return the supported features."""
        return SUPPORT_BRIGHTNESS

    @asyncio.coroutine
    def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a light command handling error messages."""
        from miio import DeviceException
        try:
            result = yield from self.hass.async_add_job(
                partial(func, *args, **kwargs))

            _LOGGER.debug("Response received from light: %s", result)

            return result == SUCCESS
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            percent_brightness = ceil(100 * brightness / 255.0)

            _LOGGER.debug(
                "Setting brightness: %s %s%%",
                brightness, percent_brightness)

            result = yield from self._try_command(
                "Setting brightness failed: %s",
                self._light.set_brightness, percent_brightness)

            if result:
                self._brightness = brightness
        else:
            yield from self._try_command(
                "Turning the light on failed.", self._light.on)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """Turn the light off."""
        yield from self._try_command(
            "Turning the light off failed.", self._light.off)

    @asyncio.coroutine
    def async_update(self):
        """Fetch state from the device."""
        from miio import DeviceException
        try:
            state = yield from self.hass.async_add_job(self._light.status)
            _LOGGER.debug("Got new state: %s", state)

            self._state = state.is_on
            self._brightness = ceil((255 / 100.0) * state.brightness)

            delayed_turn_off = self.delayed_turn_off_timestamp(
                state.delay_off_countdown,
                dt.utcnow(),
                self._state_attrs[ATTR_DELAYED_TURN_OFF])

            self._state_attrs.update({
                ATTR_SCENE: state.scene,
                ATTR_DELAYED_TURN_OFF: delayed_turn_off,
            })

        except DeviceException as ex:
            self._state = None
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    @asyncio.coroutine
    def async_set_scene(self, scene: int = 1):
        """Set the fixed scene."""
        yield from self._try_command(
            "Setting a fixed scene failed.",
            self._light.set_scene, scene)

    @asyncio.coroutine
    def async_set_delayed_turn_off(self, time_period: timedelta):
        """Set delay off. The unit is different per device."""
        yield from self._try_command(
            "Setting the delay off failed.",
            self._light.delay_off, time_period.total_seconds())

    @staticmethod
    def translate(value, left_min, left_max, right_min, right_max):
        """Map a value from left span to right span."""
        left_span = left_max - left_min
        right_span = right_max - right_min
        value_scaled = float(value - left_min) / float(left_span)
        return int(right_min + (value_scaled * right_span))

    @staticmethod
    def delayed_turn_off_timestamp(countdown: int,
                                   current: datetime,
                                   previous: datetime):
        """Update the turn off timestamp only if necessary."""
        if countdown > 0:
            new = current.replace(microsecond=0) + \
                  timedelta(seconds=countdown)

            if previous is None:
                return new

            lower = timedelta(seconds=-DELAYED_TURN_OFF_MAX_DEVIATION)
            upper = timedelta(seconds=DELAYED_TURN_OFF_MAX_DEVIATION)
            diff = previous - new
            if lower < diff < upper:
                return previous

            return new

        return None


class XiaomiPhilipsLightBall(XiaomiPhilipsGenericLight, Light):
    """Representation of a Xiaomi Philips Light Ball."""

    @property
    def color_temp(self):
        """Return the color temperature."""
        return self._color_temp

    @property
    def min_mireds(self):
        """Return the coldest color_temp that this light supports."""
        return 175

    @property
    def max_mireds(self):
        """Return the warmest color_temp that this light supports."""
        return 333

    @property
    def supported_features(self):
        """Return the supported features."""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Turn the light on."""
        if ATTR_COLOR_TEMP in kwargs:
            color_temp = kwargs[ATTR_COLOR_TEMP]
            percent_color_temp = self.translate(
                color_temp, self.max_mireds,
                self.min_mireds, CCT_MIN, CCT_MAX)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            percent_brightness = ceil(100 * brightness / 255.0)

        if ATTR_BRIGHTNESS in kwargs and ATTR_COLOR_TEMP in kwargs:
            _LOGGER.debug(
                "Setting brightness and color temperature: "
                "%s %s%%, %s mireds, %s%% cct",
                brightness, percent_brightness,
                color_temp, percent_color_temp)

            result = yield from self._try_command(
                "Setting brightness and color temperature failed: "
                "%s bri, %s cct",
                self._light.set_brightness_and_color_temperature,
                percent_brightness, percent_color_temp)

            if result:
                self._color_temp = color_temp
                self._brightness = brightness

        elif ATTR_COLOR_TEMP in kwargs:
            _LOGGER.debug(
                "Setting color temperature: "
                "%s mireds, %s%% cct",
                color_temp, percent_color_temp)

            result = yield from self._try_command(
                "Setting color temperature failed: %s cct",
                self._light.set_color_temperature, percent_color_temp)

            if result:
                self._color_temp = color_temp

        elif ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            percent_brightness = ceil(100 * brightness / 255.0)

            _LOGGER.debug(
                "Setting brightness: %s %s%%",
                brightness, percent_brightness)

            result = yield from self._try_command(
                "Setting brightness failed: %s",
                self._light.set_brightness, percent_brightness)

            if result:
                self._brightness = brightness

        else:
            yield from self._try_command(
                "Turning the light on failed.", self._light.on)

    @asyncio.coroutine
    def async_update(self):
        """Fetch state from the device."""
        from miio import DeviceException
        try:
            state = yield from self.hass.async_add_job(self._light.status)
            _LOGGER.debug("Got new state: %s", state)

            self._state = state.is_on
            self._brightness = ceil((255 / 100.0) * state.brightness)
            self._color_temp = self.translate(
                state.color_temperature,
                CCT_MIN, CCT_MAX,
                self.max_mireds, self.min_mireds)

            delayed_turn_off = self.delayed_turn_off_timestamp(
                state.delay_off_countdown,
                dt.utcnow(),
                self._state_attrs[ATTR_DELAYED_TURN_OFF])

            self._state_attrs.update({
                ATTR_SCENE: state.scene,
                ATTR_DELAYED_TURN_OFF: delayed_turn_off,
            })

        except DeviceException as ex:
            self._state = None
            _LOGGER.error("Got exception while fetching the state: %s", ex)


class XiaomiPhilipsCeilingLamp(XiaomiPhilipsLightBall, Light):
    """Representation of a Xiaomi Philips Ceiling Lamp."""

    @property
    def min_mireds(self):
        """Return the coldest color_temp that this light supports."""
        return 175

    @property
    def max_mireds(self):
        """Return the warmest color_temp that this light supports."""
        return 370


class XiaomiPhilipsEyecareLamp(XiaomiPhilipsGenericLight, Light):
    """Representation of a Xiaomi Philips Eyecare Lamp 2."""

    pass
