"""
Support for MQTT lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.mqtt/
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.core import callback
import homeassistant.components.mqtt as mqtt
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_EFFECT, ATTR_RGB_COLOR,
    ATTR_WHITE_VALUE, ATTR_XY_COLOR, Light, SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP, SUPPORT_EFFECT, SUPPORT_RGB_COLOR,
    SUPPORT_WHITE_VALUE, SUPPORT_XY_COLOR)
from homeassistant.const import (
    CONF_BRIGHTNESS, CONF_COLOR_TEMP, CONF_EFFECT, CONF_NAME,
    CONF_OPTIMISTIC, CONF_PAYLOAD_OFF, CONF_PAYLOAD_ON,
    CONF_RGB, CONF_STATE, CONF_VALUE_TEMPLATE, CONF_WHITE_VALUE, CONF_XY)
from homeassistant.components.mqtt import (
    CONF_AVAILABILITY_TOPIC, CONF_COMMAND_TOPIC, CONF_PAYLOAD_AVAILABLE,
    CONF_PAYLOAD_NOT_AVAILABLE, CONF_QOS, CONF_RETAIN, CONF_STATE_TOPIC,
    MqttAvailability)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['mqtt']

CONF_BRIGHTNESS_COMMAND_TOPIC = 'brightness_command_topic'
CONF_BRIGHTNESS_SCALE = 'brightness_scale'
CONF_BRIGHTNESS_STATE_TOPIC = 'brightness_state_topic'
CONF_BRIGHTNESS_VALUE_TEMPLATE = 'brightness_value_template'
CONF_COLOR_TEMP_COMMAND_TOPIC = 'color_temp_command_topic'
CONF_COLOR_TEMP_STATE_TOPIC = 'color_temp_state_topic'
CONF_COLOR_TEMP_VALUE_TEMPLATE = 'color_temp_value_template'
CONF_EFFECT_COMMAND_TOPIC = 'effect_command_topic'
CONF_EFFECT_LIST = 'effect_list'
CONF_EFFECT_STATE_TOPIC = 'effect_state_topic'
CONF_EFFECT_VALUE_TEMPLATE = 'effect_value_template'
CONF_RGB_COMMAND_TEMPLATE = 'rgb_command_template'
CONF_RGB_COMMAND_TOPIC = 'rgb_command_topic'
CONF_RGB_STATE_TOPIC = 'rgb_state_topic'
CONF_RGB_VALUE_TEMPLATE = 'rgb_value_template'
CONF_STATE_VALUE_TEMPLATE = 'state_value_template'
CONF_XY_COMMAND_TOPIC = 'xy_command_topic'
CONF_XY_STATE_TOPIC = 'xy_state_topic'
CONF_XY_VALUE_TEMPLATE = 'xy_value_template'
CONF_WHITE_VALUE_COMMAND_TOPIC = 'white_value_command_topic'
CONF_WHITE_VALUE_SCALE = 'white_value_scale'
CONF_WHITE_VALUE_STATE_TOPIC = 'white_value_state_topic'
CONF_WHITE_VALUE_TEMPLATE = 'white_value_template'
CONF_ON_COMMAND_TYPE = 'on_command_type'

DEFAULT_BRIGHTNESS_SCALE = 255
DEFAULT_NAME = 'MQTT Light'
DEFAULT_OPTIMISTIC = False
DEFAULT_PAYLOAD_OFF = 'OFF'
DEFAULT_PAYLOAD_ON = 'ON'
DEFAULT_WHITE_VALUE_SCALE = 255
DEFAULT_ON_COMMAND_TYPE = 'last'

VALUES_ON_COMMAND_TYPE = ['first', 'last', 'brightness']

PLATFORM_SCHEMA = mqtt.MQTT_RW_PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_BRIGHTNESS_COMMAND_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_BRIGHTNESS_SCALE, default=DEFAULT_BRIGHTNESS_SCALE):
        vol.All(vol.Coerce(int), vol.Range(min=1)),
    vol.Optional(CONF_BRIGHTNESS_STATE_TOPIC): mqtt.valid_subscribe_topic,
    vol.Optional(CONF_BRIGHTNESS_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_COLOR_TEMP_COMMAND_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_COLOR_TEMP_STATE_TOPIC): mqtt.valid_subscribe_topic,
    vol.Optional(CONF_COLOR_TEMP_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_EFFECT_COMMAND_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_EFFECT_LIST): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EFFECT_STATE_TOPIC): mqtt.valid_subscribe_topic,
    vol.Optional(CONF_EFFECT_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
    vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
    vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
    vol.Optional(CONF_RGB_COMMAND_TEMPLATE): cv.template,
    vol.Optional(CONF_RGB_COMMAND_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_RGB_STATE_TOPIC): mqtt.valid_subscribe_topic,
    vol.Optional(CONF_RGB_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_STATE_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_WHITE_VALUE_COMMAND_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_WHITE_VALUE_SCALE, default=DEFAULT_WHITE_VALUE_SCALE):
        vol.All(vol.Coerce(int), vol.Range(min=1)),
    vol.Optional(CONF_WHITE_VALUE_STATE_TOPIC): mqtt.valid_subscribe_topic,
    vol.Optional(CONF_WHITE_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_XY_COMMAND_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_XY_STATE_TOPIC): mqtt.valid_subscribe_topic,
    vol.Optional(CONF_XY_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_ON_COMMAND_TYPE, default=DEFAULT_ON_COMMAND_TYPE):
        vol.In(VALUES_ON_COMMAND_TYPE),
}).extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up a MQTT Light."""
    if discovery_info is not None:
        config = PLATFORM_SCHEMA(discovery_info)

    config.setdefault(
        CONF_STATE_VALUE_TEMPLATE, config.get(CONF_VALUE_TEMPLATE))

    async_add_devices([MqttLight(
        config.get(CONF_NAME),
        config.get(CONF_EFFECT_LIST),
        {
            key: config.get(key) for key in (
                CONF_BRIGHTNESS_COMMAND_TOPIC,
                CONF_BRIGHTNESS_STATE_TOPIC,
                CONF_COLOR_TEMP_COMMAND_TOPIC,
                CONF_COLOR_TEMP_STATE_TOPIC,
                CONF_COMMAND_TOPIC,
                CONF_EFFECT_COMMAND_TOPIC,
                CONF_EFFECT_STATE_TOPIC,
                CONF_RGB_COMMAND_TOPIC,
                CONF_RGB_STATE_TOPIC,
                CONF_STATE_TOPIC,
                CONF_WHITE_VALUE_COMMAND_TOPIC,
                CONF_WHITE_VALUE_STATE_TOPIC,
                CONF_XY_COMMAND_TOPIC,
                CONF_XY_STATE_TOPIC,
            )
        },
        {
            CONF_BRIGHTNESS: config.get(CONF_BRIGHTNESS_VALUE_TEMPLATE),
            CONF_COLOR_TEMP: config.get(CONF_COLOR_TEMP_VALUE_TEMPLATE),
            CONF_EFFECT: config.get(CONF_EFFECT_VALUE_TEMPLATE),
            CONF_RGB: config.get(CONF_RGB_VALUE_TEMPLATE),
            CONF_RGB_COMMAND_TEMPLATE: config.get(CONF_RGB_COMMAND_TEMPLATE),
            CONF_STATE: config.get(CONF_STATE_VALUE_TEMPLATE),
            CONF_WHITE_VALUE: config.get(CONF_WHITE_VALUE_TEMPLATE),
            CONF_XY: config.get(CONF_XY_VALUE_TEMPLATE),
        },
        config.get(CONF_QOS),
        config.get(CONF_RETAIN),
        {
            'on': config.get(CONF_PAYLOAD_ON),
            'off': config.get(CONF_PAYLOAD_OFF),
        },
        config.get(CONF_OPTIMISTIC),
        config.get(CONF_BRIGHTNESS_SCALE),
        config.get(CONF_WHITE_VALUE_SCALE),
        config.get(CONF_ON_COMMAND_TYPE),
        config.get(CONF_AVAILABILITY_TOPIC),
        config.get(CONF_PAYLOAD_AVAILABLE),
        config.get(CONF_PAYLOAD_NOT_AVAILABLE),
    )])


class MqttLight(MqttAvailability, Light):
    """Representation of a MQTT light."""

    def __init__(self, name, effect_list, topic, templates, qos,
                 retain, payload, optimistic, brightness_scale,
                 white_value_scale, on_command_type, availability_topic,
                 payload_available, payload_not_available):
        """Initialize MQTT light."""
        super().__init__(availability_topic, qos, payload_available,
                         payload_not_available)
        self._name = name
        self._effect_list = effect_list
        self._topic = topic
        self._qos = qos
        self._retain = retain
        self._payload = payload
        self._templates = templates
        self._optimistic = optimistic or topic[CONF_STATE_TOPIC] is None
        self._optimistic_rgb = \
            optimistic or topic[CONF_RGB_STATE_TOPIC] is None
        self._optimistic_brightness = (
            optimistic or topic[CONF_BRIGHTNESS_STATE_TOPIC] is None)
        self._optimistic_color_temp = (
            optimistic or topic[CONF_COLOR_TEMP_STATE_TOPIC] is None)
        self._optimistic_effect = (
            optimistic or topic[CONF_EFFECT_STATE_TOPIC] is None)
        self._optimistic_white_value = (
            optimistic or topic[CONF_WHITE_VALUE_STATE_TOPIC] is None)
        self._optimistic_xy = \
            optimistic or topic[CONF_XY_STATE_TOPIC] is None
        self._brightness_scale = brightness_scale
        self._white_value_scale = white_value_scale
        self._on_command_type = on_command_type
        self._state = False
        self._brightness = None
        self._rgb = None
        self._color_temp = None
        self._effect = None
        self._white_value = None
        self._xy = None
        self._supported_features = 0
        self._supported_features |= (
            topic[CONF_RGB_COMMAND_TOPIC] is not None and SUPPORT_RGB_COLOR)
        self._supported_features |= (
            topic[CONF_BRIGHTNESS_COMMAND_TOPIC] is not None and
            SUPPORT_BRIGHTNESS)
        self._supported_features |= (
            topic[CONF_COLOR_TEMP_COMMAND_TOPIC] is not None and
            SUPPORT_COLOR_TEMP)
        self._supported_features |= (
            topic[CONF_EFFECT_STATE_TOPIC] is not None and
            SUPPORT_EFFECT)
        self._supported_features |= (
            topic[CONF_WHITE_VALUE_COMMAND_TOPIC] is not None and
            SUPPORT_WHITE_VALUE)
        self._supported_features |= (
            topic[CONF_XY_COMMAND_TOPIC] is not None and SUPPORT_XY_COLOR)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Subscribe to MQTT events."""
        yield from super().async_added_to_hass()

        templates = {}
        for key, tpl in list(self._templates.items()):
            if tpl is None:
                templates[key] = lambda value: value
            else:
                tpl.hass = self.hass
                templates[key] = tpl.async_render_with_possible_json_value

        @callback
        def state_received(topic, payload, qos):
            """Handle new MQTT messages."""
            payload = templates[CONF_STATE](payload)
            if payload == self._payload['on']:
                self._state = True
            elif payload == self._payload['off']:
                self._state = False
            self.async_schedule_update_ha_state()

        if self._topic[CONF_STATE_TOPIC] is not None:
            yield from mqtt.async_subscribe(
                self.hass, self._topic[CONF_STATE_TOPIC], state_received,
                self._qos)

        @callback
        def brightness_received(topic, payload, qos):
            """Handle new MQTT messages for the brightness."""
            device_value = float(templates[CONF_BRIGHTNESS](payload))
            percent_bright = device_value / self._brightness_scale
            self._brightness = int(percent_bright * 255)
            self.async_schedule_update_ha_state()

        if self._topic[CONF_BRIGHTNESS_STATE_TOPIC] is not None:
            yield from mqtt.async_subscribe(
                self.hass, self._topic[CONF_BRIGHTNESS_STATE_TOPIC],
                brightness_received, self._qos)
            self._brightness = 255
        elif self._topic[CONF_BRIGHTNESS_COMMAND_TOPIC] is not None:
            self._brightness = 255
        else:
            self._brightness = None

        @callback
        def rgb_received(topic, payload, qos):
            """Handle new MQTT messages for RGB."""
            self._rgb = [int(val) for val in
                         templates[CONF_RGB](payload).split(',')]
            self.async_schedule_update_ha_state()

        if self._topic[CONF_RGB_STATE_TOPIC] is not None:
            yield from mqtt.async_subscribe(
                self.hass, self._topic[CONF_RGB_STATE_TOPIC], rgb_received,
                self._qos)
            self._rgb = [255, 255, 255]
        if self._topic[CONF_RGB_COMMAND_TOPIC] is not None:
            self._rgb = [255, 255, 255]
        else:
            self._rgb = None

        @callback
        def color_temp_received(topic, payload, qos):
            """Handle new MQTT messages for color temperature."""
            self._color_temp = int(templates[CONF_COLOR_TEMP](payload))
            self.async_schedule_update_ha_state()

        if self._topic[CONF_COLOR_TEMP_STATE_TOPIC] is not None:
            yield from mqtt.async_subscribe(
                self.hass, self._topic[CONF_COLOR_TEMP_STATE_TOPIC],
                color_temp_received, self._qos)
            self._color_temp = 150
        if self._topic[CONF_COLOR_TEMP_COMMAND_TOPIC] is not None:
            self._color_temp = 150
        else:
            self._color_temp = None

        @callback
        def effect_received(topic, payload, qos):
            """Handle new MQTT messages for effect."""
            self._effect = templates[CONF_EFFECT](payload)
            self.async_schedule_update_ha_state()

        if self._topic[CONF_EFFECT_STATE_TOPIC] is not None:
            yield from mqtt.async_subscribe(
                self.hass, self._topic[CONF_EFFECT_STATE_TOPIC],
                effect_received, self._qos)
            self._effect = 'none'
        if self._topic[CONF_EFFECT_COMMAND_TOPIC] is not None:
            self._effect = 'none'
        else:
            self._effect = None

        @callback
        def white_value_received(topic, payload, qos):
            """Handle new MQTT messages for white value."""
            device_value = float(templates[CONF_WHITE_VALUE](payload))
            percent_white = device_value / self._white_value_scale
            self._white_value = int(percent_white * 255)
            self.async_schedule_update_ha_state()

        if self._topic[CONF_WHITE_VALUE_STATE_TOPIC] is not None:
            yield from mqtt.async_subscribe(
                self.hass, self._topic[CONF_WHITE_VALUE_STATE_TOPIC],
                white_value_received, self._qos)
            self._white_value = 255
        elif self._topic[CONF_WHITE_VALUE_COMMAND_TOPIC] is not None:
            self._white_value = 255
        else:
            self._white_value = None

        @callback
        def xy_received(topic, payload, qos):
            """Handle new MQTT messages for  color."""
            self._xy = [float(val) for val in
                        templates[CONF_XY](payload).split(',')]
            self.async_schedule_update_ha_state()

        if self._topic[CONF_XY_STATE_TOPIC] is not None:
            yield from mqtt.async_subscribe(
                self.hass, self._topic[CONF_XY_STATE_TOPIC], xy_received,
                self._qos)
            self._xy = [1, 1]
        if self._topic[CONF_XY_COMMAND_TOPIC] is not None:
            self._xy = [1, 1]
        else:
            self._xy = None

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the RGB color value."""
        return self._rgb

    @property
    def color_temp(self):
        """Return the color temperature in mired."""
        return self._color_temp

    @property
    def white_value(self):
        """Return the white property."""
        return self._white_value

    @property
    def xy_color(self):
        """Return the RGB color value."""
        return self._xy

    @property
    def should_poll(self):
        """No polling needed for a MQTT light."""
        return False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return self._optimistic

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Turn the device on.

        This method is a coroutine.
        """
        should_update = False

        if self._on_command_type == 'first':
            mqtt.async_publish(
                self.hass, self._topic[CONF_COMMAND_TOPIC],
                self._payload['on'], self._qos, self._retain)
            should_update = True

        # If brightness is being used instead of an on command, make sure
        # there is a brightness input.  Either set the brightness to our
        # saved value or the maximum value if this is the first call
        elif self._on_command_type == 'brightness':
            if ATTR_BRIGHTNESS not in kwargs:
                kwargs[ATTR_BRIGHTNESS] = self._brightness if \
                                          self._brightness else 255

        if ATTR_RGB_COLOR in kwargs and \
           self._topic[CONF_RGB_COMMAND_TOPIC] is not None:

            tpl = self._templates[CONF_RGB_COMMAND_TEMPLATE]
            if tpl:
                colors = ('red', 'green', 'blue')
                variables = {key: val for key, val in
                             zip(colors, kwargs[ATTR_RGB_COLOR])}
                rgb_color_str = tpl.async_render(variables)
            else:
                rgb_color_str = '{},{},{}'.format(*kwargs[ATTR_RGB_COLOR])

            mqtt.async_publish(
                self.hass, self._topic[CONF_RGB_COMMAND_TOPIC],
                rgb_color_str, self._qos, self._retain)

            if self._optimistic_rgb:
                self._rgb = kwargs[ATTR_RGB_COLOR]
                should_update = True

        if ATTR_BRIGHTNESS in kwargs and \
           self._topic[CONF_BRIGHTNESS_COMMAND_TOPIC] is not None:
            percent_bright = float(kwargs[ATTR_BRIGHTNESS]) / 255
            device_brightness = int(percent_bright * self._brightness_scale)
            mqtt.async_publish(
                self.hass, self._topic[CONF_BRIGHTNESS_COMMAND_TOPIC],
                device_brightness, self._qos, self._retain)

            if self._optimistic_brightness:
                self._brightness = kwargs[ATTR_BRIGHTNESS]
                should_update = True

        if ATTR_COLOR_TEMP in kwargs and \
           self._topic[CONF_COLOR_TEMP_COMMAND_TOPIC] is not None:
            color_temp = int(kwargs[ATTR_COLOR_TEMP])
            mqtt.async_publish(
                self.hass, self._topic[CONF_COLOR_TEMP_COMMAND_TOPIC],
                color_temp, self._qos, self._retain)

            if self._optimistic_color_temp:
                self._color_temp = kwargs[ATTR_COLOR_TEMP]
                should_update = True

        if ATTR_EFFECT in kwargs and \
           self._topic[CONF_EFFECT_COMMAND_TOPIC] is not None:
            effect = kwargs[ATTR_EFFECT]
            if effect in self._effect_list:
                mqtt.async_publish(
                    self.hass, self._topic[CONF_EFFECT_COMMAND_TOPIC],
                    effect, self._qos, self._retain)

                if self._optimistic_effect:
                    self._effect = kwargs[ATTR_EFFECT]
                    should_update = True

        if ATTR_WHITE_VALUE in kwargs and \
           self._topic[CONF_WHITE_VALUE_COMMAND_TOPIC] is not None:
            percent_white = float(kwargs[ATTR_WHITE_VALUE]) / 255
            device_white_value = int(percent_white * self._white_value_scale)
            mqtt.async_publish(
                self.hass, self._topic[CONF_WHITE_VALUE_COMMAND_TOPIC],
                device_white_value, self._qos, self._retain)

            if self._optimistic_white_value:
                self._white_value = kwargs[ATTR_WHITE_VALUE]
                should_update = True

        if ATTR_XY_COLOR in kwargs and \
           self._topic[CONF_XY_COMMAND_TOPIC] is not None:

            mqtt.async_publish(
                self.hass, self._topic[CONF_XY_COMMAND_TOPIC],
                '{},{}'.format(*kwargs[ATTR_XY_COLOR]), self._qos,
                self._retain)

            if self._optimistic_xy:
                self._xy = kwargs[ATTR_XY_COLOR]
                should_update = True

        if self._on_command_type == 'last':
            mqtt.async_publish(self.hass, self._topic[CONF_COMMAND_TOPIC],
                               self._payload['on'], self._qos, self._retain)
            should_update = True

        if self._optimistic:
            # Optimistically assume that switch has changed state.
            self._state = True
            should_update = True

        if should_update:
            self.async_schedule_update_ha_state()

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """Turn the device off.

        This method is a coroutine.
        """
        mqtt.async_publish(
            self.hass, self._topic[CONF_COMMAND_TOPIC], self._payload['off'],
            self._qos, self._retain)

        if self._optimistic:
            # Optimistically assume that switch has changed state.
            self._state = False
            self.async_schedule_update_ha_state()
