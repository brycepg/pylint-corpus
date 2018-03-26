"""
This component provides light support for the Philips Hue system.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.hue/
"""
import asyncio
from datetime import timedelta
import logging
import random
import re
import socket

import voluptuous as vol

import homeassistant.components.hue as hue
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_EFFECT, ATTR_FLASH, ATTR_RGB_COLOR,
    ATTR_TRANSITION, ATTR_XY_COLOR, EFFECT_COLORLOOP, EFFECT_RANDOM,
    FLASH_LONG, FLASH_SHORT, PLATFORM_SCHEMA, SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP, SUPPORT_EFFECT, SUPPORT_FLASH, SUPPORT_RGB_COLOR,
    SUPPORT_TRANSITION, SUPPORT_XY_COLOR, Light)
from homeassistant.const import CONF_FILENAME, CONF_HOST, DEVICE_DEFAULT_NAME
import homeassistant.helpers.config_validation as cv
import homeassistant.util as util
from homeassistant.util import yaml
import homeassistant.util.color as color_util

DEPENDENCIES = ['hue']

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(milliseconds=100)

SUPPORT_HUE_ON_OFF = (SUPPORT_FLASH | SUPPORT_TRANSITION)
SUPPORT_HUE_DIMMABLE = (SUPPORT_HUE_ON_OFF | SUPPORT_BRIGHTNESS)
SUPPORT_HUE_COLOR_TEMP = (SUPPORT_HUE_DIMMABLE | SUPPORT_COLOR_TEMP)
SUPPORT_HUE_COLOR = (SUPPORT_HUE_DIMMABLE | SUPPORT_EFFECT |
                     SUPPORT_RGB_COLOR | SUPPORT_XY_COLOR)
SUPPORT_HUE_EXTENDED = (SUPPORT_HUE_COLOR_TEMP | SUPPORT_HUE_COLOR)

SUPPORT_HUE = {
    'Extended color light': SUPPORT_HUE_EXTENDED,
    'Color light': SUPPORT_HUE_COLOR,
    'Dimmable light': SUPPORT_HUE_DIMMABLE,
    'On/Off plug-in unit': SUPPORT_HUE_ON_OFF,
    'Color temperature light': SUPPORT_HUE_COLOR_TEMP
    }

ATTR_EMULATED_HUE_HIDDEN = 'emulated_hue_hidden'
ATTR_IS_HUE_GROUP = 'is_hue_group'

# Legacy configuration, will be removed in 0.60
CONF_ALLOW_UNREACHABLE = 'allow_unreachable'
DEFAULT_ALLOW_UNREACHABLE = False
CONF_ALLOW_IN_EMULATED_HUE = 'allow_in_emulated_hue'
DEFAULT_ALLOW_IN_EMULATED_HUE = True
CONF_ALLOW_HUE_GROUPS = 'allow_hue_groups'
DEFAULT_ALLOW_HUE_GROUPS = True

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST): cv.string,
    vol.Optional(CONF_ALLOW_UNREACHABLE): cv.boolean,
    vol.Optional(CONF_FILENAME): cv.string,
    vol.Optional(CONF_ALLOW_IN_EMULATED_HUE): cv.boolean,
    vol.Optional(CONF_ALLOW_HUE_GROUPS,
                 default=DEFAULT_ALLOW_HUE_GROUPS): cv.boolean,
})

MIGRATION_ID = 'light_hue_config_migration'
MIGRATION_TITLE = 'Philips Hue Configuration Migration'
MIGRATION_INSTRUCTIONS = """
Configuration for the Philips Hue component has changed; action required.

You have configured at least one bridge:

    hue:
{config}

This configuration is deprecated, please check the
[Hue component](https://home-assistant.io/components/hue/) page for more
information.
"""

SIGNAL_CALLBACK = 'hue_light_callback_{}_{}'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Hue lights."""
    if discovery_info is None or 'bridge_id' not in discovery_info:
        return

    if config is not None and config:
        # Legacy configuration, will be removed in 0.60
        config_str = yaml.dump([config])
        # Indent so it renders in a fixed-width font
        config_str = re.sub('(?m)^', '      ', config_str)
        hass.components.persistent_notification.async_create(
            MIGRATION_INSTRUCTIONS.format(config=config_str),
            title=MIGRATION_TITLE,
            notification_id=MIGRATION_ID)

    bridge_id = discovery_info['bridge_id']
    bridge = hass.data[hue.DOMAIN][bridge_id]
    unthrottled_update_lights(hass, bridge, add_devices)


@util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
def update_lights(hass, bridge, add_devices):
    """Update the Hue light objects with latest info from the bridge."""
    return unthrottled_update_lights(hass, bridge, add_devices)


def unthrottled_update_lights(hass, bridge, add_devices):
    """Update the lights (Internal version of update_lights)."""
    import phue

    if not bridge.configured:
        return

    try:
        api = bridge.get_api()
    except phue.PhueRequestTimeout:
        _LOGGER.warning("Timeout trying to reach the bridge")
        bridge.available = False
        return
    except ConnectionRefusedError:
        _LOGGER.error("The bridge refused the connection")
        bridge.available = False
        return
    except socket.error:
        # socket.error when we cannot reach Hue
        _LOGGER.exception("Cannot reach the bridge")
        bridge.available = False
        return

    bridge.available = True

    new_lights = process_lights(
        hass, api, bridge,
        lambda **kw: update_lights(hass, bridge, add_devices, **kw))
    if bridge.allow_hue_groups:
        new_lightgroups = process_groups(
            hass, api, bridge,
            lambda **kw: update_lights(hass, bridge, add_devices, **kw))
        new_lights.extend(new_lightgroups)

    if new_lights:
        add_devices(new_lights)


def process_lights(hass, api, bridge, update_lights_cb):
    """Set up HueLight objects for all lights."""
    api_lights = api.get('lights')

    if not isinstance(api_lights, dict):
        _LOGGER.error("Got unexpected result from Hue API")
        return []

    new_lights = []

    for light_id, info in api_lights.items():
        if light_id not in bridge.lights:
            bridge.lights[light_id] = HueLight(
                int(light_id), info, bridge,
                update_lights_cb,
                bridge.allow_unreachable,
                bridge.allow_in_emulated_hue)
            new_lights.append(bridge.lights[light_id])
        else:
            bridge.lights[light_id].info = info
            hass.helpers.dispatcher.dispatcher_send(
                SIGNAL_CALLBACK.format(
                    bridge.bridge_id,
                    bridge.lights[light_id].light_id))

    return new_lights


def process_groups(hass, api, bridge, update_lights_cb):
    """Set up HueLight objects for all groups."""
    api_groups = api.get('groups')

    if not isinstance(api_groups, dict):
        _LOGGER.error('Got unexpected result from Hue API')
        return []

    new_lights = []

    for lightgroup_id, info in api_groups.items():
        if 'state' not in info:
            _LOGGER.warning(
                "Group info does not contain state. Please update your hub")
            return []

        if lightgroup_id not in bridge.lightgroups:
            bridge.lightgroups[lightgroup_id] = HueLight(
                int(lightgroup_id), info, bridge,
                update_lights_cb,
                bridge.allow_unreachable,
                bridge.allow_in_emulated_hue, True)
            new_lights.append(bridge.lightgroups[lightgroup_id])
        else:
            bridge.lightgroups[lightgroup_id].info = info
            hass.helpers.dispatcher.dispatcher_send(
                SIGNAL_CALLBACK.format(
                    bridge.bridge_id,
                    bridge.lightgroups[lightgroup_id].light_id))

    return new_lights


class HueLight(Light):
    """Representation of a Hue light."""

    def __init__(self, light_id, info, bridge, update_lights_cb,
                 allow_unreachable, allow_in_emulated_hue, is_group=False):
        """Initialize the light."""
        self.light_id = light_id
        self.info = info
        self.bridge = bridge
        self.update_lights = update_lights_cb
        self.allow_unreachable = allow_unreachable
        self.is_group = is_group
        self.allow_in_emulated_hue = allow_in_emulated_hue

        if is_group:
            self._command_func = self.bridge.set_group
        else:
            self._command_func = self.bridge.set_light

    @property
    def unique_id(self):
        """Return the ID of this Hue light."""
        return self.info.get('uniqueid')

    @property
    def name(self):
        """Return the name of the Hue light."""
        return self.info.get('name', DEVICE_DEFAULT_NAME)

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        if self.is_group:
            return self.info['action'].get('bri')
        return self.info['state'].get('bri')

    @property
    def xy_color(self):
        """Return the XY color value."""
        if self.is_group:
            return self.info['action'].get('xy')
        return self.info['state'].get('xy')

    @property
    def color_temp(self):
        """Return the CT color value."""
        if self.is_group:
            return self.info['action'].get('ct')
        return self.info['state'].get('ct')

    @property
    def is_on(self):
        """Return true if device is on."""
        if self.is_group:
            return self.info['state']['any_on']
        return self.info['state']['on']

    @property
    def available(self):
        """Return if light is available."""
        return self.bridge.available and (self.is_group or
                                          self.allow_unreachable or
                                          self.info['state']['reachable'])

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_HUE.get(self.info.get('type'), SUPPORT_HUE_EXTENDED)

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return [EFFECT_COLORLOOP, EFFECT_RANDOM]

    def turn_on(self, **kwargs):
        """Turn the specified or all lights on."""
        command = {'on': True}

        if ATTR_TRANSITION in kwargs:
            command['transitiontime'] = int(kwargs[ATTR_TRANSITION] * 10)

        if ATTR_XY_COLOR in kwargs:
            if self.info.get('manufacturername') == 'OSRAM':
                color_hue, sat = color_util.color_xy_to_hs(
                    *kwargs[ATTR_XY_COLOR])
                command['hue'] = color_hue / 360 * 65535
                command['sat'] = sat / 100 * 255
            else:
                command['xy'] = kwargs[ATTR_XY_COLOR]
        elif ATTR_RGB_COLOR in kwargs:
            if self.info.get('manufacturername') == 'OSRAM':
                hsv = color_util.color_RGB_to_hsv(
                    *(int(val) for val in kwargs[ATTR_RGB_COLOR]))
                command['hue'] = hsv[0] / 360 * 65535
                command['sat'] = hsv[1] / 100 * 255
                command['bri'] = hsv[2] / 100 * 255
            else:
                xyb = color_util.color_RGB_to_xy(
                    *(int(val) for val in kwargs[ATTR_RGB_COLOR]))
                command['xy'] = xyb[0], xyb[1]
        elif ATTR_COLOR_TEMP in kwargs:
            temp = kwargs[ATTR_COLOR_TEMP]
            command['ct'] = max(self.min_mireds, min(temp, self.max_mireds))

        if ATTR_BRIGHTNESS in kwargs:
            command['bri'] = kwargs[ATTR_BRIGHTNESS]

        flash = kwargs.get(ATTR_FLASH)

        if flash == FLASH_LONG:
            command['alert'] = 'lselect'
            del command['on']
        elif flash == FLASH_SHORT:
            command['alert'] = 'select'
            del command['on']
        else:
            command['alert'] = 'none'

        effect = kwargs.get(ATTR_EFFECT)

        if effect == EFFECT_COLORLOOP:
            command['effect'] = 'colorloop'
        elif effect == EFFECT_RANDOM:
            command['hue'] = random.randrange(0, 65535)
            command['sat'] = random.randrange(150, 254)
        elif self.info.get('manufacturername') == 'Philips':
            command['effect'] = 'none'

        self._command_func(self.light_id, command)

    def turn_off(self, **kwargs):
        """Turn the specified or all lights off."""
        command = {'on': False}

        if ATTR_TRANSITION in kwargs:
            command['transitiontime'] = int(kwargs[ATTR_TRANSITION] * 10)

        flash = kwargs.get(ATTR_FLASH)

        if flash == FLASH_LONG:
            command['alert'] = 'lselect'
            del command['on']
        elif flash == FLASH_SHORT:
            command['alert'] = 'select'
            del command['on']
        else:
            command['alert'] = 'none'

        self._command_func(self.light_id, command)

    def update(self):
        """Synchronize state with bridge."""
        self.update_lights(no_throttle=True)

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attributes = {}
        if not self.allow_in_emulated_hue:
            attributes[ATTR_EMULATED_HUE_HIDDEN] = \
                not self.allow_in_emulated_hue
        if self.is_group:
            attributes[ATTR_IS_HUE_GROUP] = self.is_group
        return attributes

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register update callback."""
        dev_id = self.bridge.bridge_id, self.light_id
        self.hass.helpers.dispatcher.async_dispatcher_connect(
            SIGNAL_CALLBACK.format(*dev_id),
            self.async_schedule_update_ha_state)
