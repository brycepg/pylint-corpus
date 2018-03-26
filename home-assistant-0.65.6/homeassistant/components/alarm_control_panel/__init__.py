"""
Component to interface with an alarm control panel.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel/
"""
import asyncio
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.const import (
    ATTR_CODE, ATTR_CODE_FORMAT, ATTR_ENTITY_ID, SERVICE_ALARM_TRIGGER,
    SERVICE_ALARM_DISARM, SERVICE_ALARM_ARM_HOME, SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_NIGHT, SERVICE_ALARM_ARM_CUSTOM_BYPASS)
from homeassistant.loader import bind_hass
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA  # noqa
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent

DOMAIN = 'alarm_control_panel'
SCAN_INTERVAL = timedelta(seconds=30)
ATTR_CHANGED_BY = 'changed_by'

ENTITY_ID_FORMAT = DOMAIN + '.{}'

SERVICE_TO_METHOD = {
    SERVICE_ALARM_DISARM: 'alarm_disarm',
    SERVICE_ALARM_ARM_HOME: 'alarm_arm_home',
    SERVICE_ALARM_ARM_AWAY: 'alarm_arm_away',
    SERVICE_ALARM_ARM_NIGHT: 'alarm_arm_night',
    SERVICE_ALARM_ARM_CUSTOM_BYPASS: 'alarm_arm_custom_bypass',
    SERVICE_ALARM_TRIGGER: 'alarm_trigger'
}

ATTR_TO_PROPERTY = [
    ATTR_CODE,
    ATTR_CODE_FORMAT
]

ALARM_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Optional(ATTR_CODE): cv.string,
})


@bind_hass
def alarm_disarm(hass, code=None, entity_id=None):
    """Send the alarm the command for disarm."""
    data = {}
    if code:
        data[ATTR_CODE] = code
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_ALARM_DISARM, data)


@bind_hass
def alarm_arm_home(hass, code=None, entity_id=None):
    """Send the alarm the command for arm home."""
    data = {}
    if code:
        data[ATTR_CODE] = code
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_ALARM_ARM_HOME, data)


@bind_hass
def alarm_arm_away(hass, code=None, entity_id=None):
    """Send the alarm the command for arm away."""
    data = {}
    if code:
        data[ATTR_CODE] = code
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_ALARM_ARM_AWAY, data)


@bind_hass
def alarm_arm_night(hass, code=None, entity_id=None):
    """Send the alarm the command for arm night."""
    data = {}
    if code:
        data[ATTR_CODE] = code
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_ALARM_ARM_NIGHT, data)


@bind_hass
def alarm_trigger(hass, code=None, entity_id=None):
    """Send the alarm the command for trigger."""
    data = {}
    if code:
        data[ATTR_CODE] = code
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_ALARM_TRIGGER, data)


@bind_hass
def alarm_arm_custom_bypass(hass, code=None, entity_id=None):
    """Send the alarm the command for arm custom bypass."""
    data = {}
    if code:
        data[ATTR_CODE] = code
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_ALARM_ARM_CUSTOM_BYPASS, data)


@asyncio.coroutine
def async_setup(hass, config):
    """Track states and offer events for sensors."""
    component = EntityComponent(
        logging.getLogger(__name__), DOMAIN, hass, SCAN_INTERVAL)

    yield from component.async_setup(config)

    @asyncio.coroutine
    def async_alarm_service_handler(service):
        """Map services to methods on Alarm."""
        target_alarms = component.async_extract_from_service(service)

        code = service.data.get(ATTR_CODE)

        method = "async_{}".format(SERVICE_TO_METHOD[service.service])

        update_tasks = []
        for alarm in target_alarms:
            yield from getattr(alarm, method)(code)

            if not alarm.should_poll:
                continue
            update_tasks.append(alarm.async_update_ha_state(True))

        if update_tasks:
            yield from asyncio.wait(update_tasks, loop=hass.loop)

    for service in SERVICE_TO_METHOD:
        hass.services.async_register(
            DOMAIN, service, async_alarm_service_handler,
            schema=ALARM_SERVICE_SCHEMA)

    return True


# pylint: disable=no-self-use
class AlarmControlPanel(Entity):
    """An abstract class for alarm control devices."""

    @property
    def code_format(self):
        """Regex for code format or None if no code is required."""
        return None

    @property
    def changed_by(self):
        """Last change triggered by."""
        return None

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        raise NotImplementedError()

    def async_alarm_disarm(self, code=None):
        """Send disarm command.

        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.alarm_disarm, code)

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        raise NotImplementedError()

    def async_alarm_arm_home(self, code=None):
        """Send arm home command.

        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.alarm_arm_home, code)

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        raise NotImplementedError()

    def async_alarm_arm_away(self, code=None):
        """Send arm away command.

        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.alarm_arm_away, code)

    def alarm_arm_night(self, code=None):
        """Send arm night command."""
        raise NotImplementedError()

    def async_alarm_arm_night(self, code=None):
        """Send arm night command.

        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.alarm_arm_night, code)

    def alarm_trigger(self, code=None):
        """Send alarm trigger command."""
        raise NotImplementedError()

    def async_alarm_trigger(self, code=None):
        """Send alarm trigger command.

        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.alarm_trigger, code)

    def alarm_arm_custom_bypass(self, code=None):
        """Send arm custom bypass command."""
        raise NotImplementedError()

    def async_alarm_arm_custom_bypass(self, code=None):
        """Send arm custom bypass command.

        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.alarm_arm_custom_bypass, code)

    @property
    def state_attributes(self):
        """Return the state attributes."""
        state_attr = {
            ATTR_CODE_FORMAT: self.code_format,
            ATTR_CHANGED_BY: self.changed_by
        }
        return state_attr
