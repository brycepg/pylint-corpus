"""
Component to offer a way to set a numeric value from a slider or text box.

For more details about this component, please refer to the documentation
at https://home-assistant.io/components/input_number/
"""
import asyncio
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, CONF_ICON, CONF_NAME, CONF_MODE)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import async_get_last_state
from homeassistant.loader import bind_hass

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'input_number'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

CONF_INITIAL = 'initial'
CONF_MIN = 'min'
CONF_MAX = 'max'
CONF_STEP = 'step'

MODE_SLIDER = 'slider'
MODE_BOX = 'box'

ATTR_VALUE = 'value'
ATTR_MIN = 'min'
ATTR_MAX = 'max'
ATTR_STEP = 'step'
ATTR_MODE = 'mode'

SERVICE_SET_VALUE = 'set_value'
SERVICE_INCREMENT = 'increment'
SERVICE_DECREMENT = 'decrement'

SERVICE_DEFAULT_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids
})

SERVICE_SET_VALUE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_VALUE): vol.Coerce(float),
})


def _cv_input_number(cfg):
    """Configure validation helper for input number (voluptuous)."""
    minimum = cfg.get(CONF_MIN)
    maximum = cfg.get(CONF_MAX)
    if minimum >= maximum:
        raise vol.Invalid('Maximum ({}) is not greater than minimum ({})'
                          .format(minimum, maximum))
    state = cfg.get(CONF_INITIAL)
    if state is not None and (state < minimum or state > maximum):
        raise vol.Invalid('Initial value {} not in range {}-{}'
                          .format(state, minimum, maximum))
    return cfg


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        cv.slug: vol.All({
            vol.Optional(CONF_NAME): cv.string,
            vol.Required(CONF_MIN): vol.Coerce(float),
            vol.Required(CONF_MAX): vol.Coerce(float),
            vol.Optional(CONF_INITIAL): vol.Coerce(float),
            vol.Optional(CONF_STEP, default=1):
                vol.All(vol.Coerce(float), vol.Range(min=1e-3)),
            vol.Optional(CONF_ICON): cv.icon,
            vol.Optional(ATTR_UNIT_OF_MEASUREMENT): cv.string,
            vol.Optional(CONF_MODE, default=MODE_SLIDER):
                vol.In([MODE_BOX, MODE_SLIDER]),
        }, _cv_input_number)
    })
}, required=True, extra=vol.ALLOW_EXTRA)


SERVICE_TO_METHOD = {
    SERVICE_SET_VALUE: {
        'method': 'async_set_value',
        'schema': SERVICE_SET_VALUE_SCHEMA},
    SERVICE_INCREMENT: {
        'method': 'async_increment',
        'schema': SERVICE_DEFAULT_SCHEMA},
    SERVICE_DECREMENT: {
        'method': 'async_decrement',
        'schema': SERVICE_DEFAULT_SCHEMA},
}


@bind_hass
def set_value(hass, entity_id, value):
    """Set input_number to value."""
    hass.services.call(DOMAIN, SERVICE_SET_VALUE, {
        ATTR_ENTITY_ID: entity_id,
        ATTR_VALUE: value,
    })


@bind_hass
def increment(hass, entity_id):
    """Increment value of entity."""
    hass.services.call(DOMAIN, SERVICE_INCREMENT, {
        ATTR_ENTITY_ID: entity_id
    })


@bind_hass
def decrement(hass, entity_id):
    """Decrement value of entity."""
    hass.services.call(DOMAIN, SERVICE_DECREMENT, {
        ATTR_ENTITY_ID: entity_id
    })


@asyncio.coroutine
def async_setup(hass, config):
    """Set up an input slider."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []

    for object_id, cfg in config[DOMAIN].items():
        name = cfg.get(CONF_NAME)
        minimum = cfg.get(CONF_MIN)
        maximum = cfg.get(CONF_MAX)
        initial = cfg.get(CONF_INITIAL)
        step = cfg.get(CONF_STEP)
        icon = cfg.get(CONF_ICON)
        unit = cfg.get(ATTR_UNIT_OF_MEASUREMENT)
        mode = cfg.get(CONF_MODE)

        entities.append(InputNumber(
            object_id, name, initial, minimum, maximum, step, icon, unit,
            mode))

    if not entities:
        return False

    @asyncio.coroutine
    def async_handle_service(service):
        """Handle calls to input_number services."""
        target_inputs = component.async_extract_from_service(service)
        method = SERVICE_TO_METHOD.get(service.service)
        params = service.data.copy()
        params.pop(ATTR_ENTITY_ID, None)

        # call method
        update_tasks = []
        for target_input in target_inputs:
            yield from getattr(target_input, method['method'])(**params)
            if not target_input.should_poll:
                continue
            update_tasks.append(target_input.async_update_ha_state(True))

        if update_tasks:
            yield from asyncio.wait(update_tasks, loop=hass.loop)

    for service, data in SERVICE_TO_METHOD.items():
        hass.services.async_register(
            DOMAIN, service, async_handle_service, schema=data['schema'])

    yield from component.async_add_entities(entities)
    return True


class InputNumber(Entity):
    """Representation of a slider."""

    def __init__(self, object_id, name, initial, minimum, maximum, step, icon,
                 unit, mode):
        """Initialize an input number."""
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._name = name
        self._current_value = initial
        self._minimum = minimum
        self._maximum = maximum
        self._step = step
        self._icon = icon
        self._unit = unit
        self._mode = mode

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the input slider."""
        return self._name

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    @property
    def state(self):
        """Return the state of the component."""
        return self._current_value

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_MIN: self._minimum,
            ATTR_MAX: self._maximum,
            ATTR_STEP: self._step,
            ATTR_MODE: self._mode,
        }

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        if self._current_value is not None:
            return

        state = yield from async_get_last_state(self.hass, self.entity_id)
        value = state and float(state.state)

        # Check against None because value can be 0
        if value is not None and self._minimum <= value <= self._maximum:
            self._current_value = value
        else:
            self._current_value = self._minimum

    @asyncio.coroutine
    def async_set_value(self, value):
        """Set new value."""
        num_value = float(value)
        if num_value < self._minimum or num_value > self._maximum:
            _LOGGER.warning("Invalid value: %s (range %s - %s)",
                            num_value, self._minimum, self._maximum)
            return
        self._current_value = num_value
        yield from self.async_update_ha_state()

    @asyncio.coroutine
    def async_increment(self):
        """Increment value."""
        new_value = self._current_value + self._step
        if new_value > self._maximum:
            _LOGGER.warning("Invalid value: %s (range %s - %s)",
                            new_value, self._minimum, self._maximum)
            return
        self._current_value = new_value
        yield from self.async_update_ha_state()

    @asyncio.coroutine
    def async_decrement(self):
        """Decrement value."""
        new_value = self._current_value - self._step
        if new_value < self._minimum:
            _LOGGER.warning("Invalid value: %s (range %s - %s)",
                            new_value, self._minimum, self._maximum)
            return
        self._current_value = new_value
        yield from self.async_update_ha_state()
