"""The tests for the Demo vacuum platform."""
import unittest

from homeassistant.components import vacuum
from homeassistant.components.vacuum import (
    ATTR_BATTERY_LEVEL, ATTR_COMMAND, ATTR_ENTITY_ID, ATTR_FAN_SPEED,
    ATTR_FAN_SPEED_LIST, ATTR_PARAMS, ATTR_STATUS, DOMAIN,
    ENTITY_ID_ALL_VACUUMS,
    SERVICE_SEND_COMMAND, SERVICE_SET_FAN_SPEED)
from homeassistant.components.vacuum.demo import (
    DEMO_VACUUM_BASIC, DEMO_VACUUM_COMPLETE, DEMO_VACUUM_MINIMAL,
    DEMO_VACUUM_MOST, DEMO_VACUUM_NONE, FAN_SPEEDS)
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES, CONF_PLATFORM, STATE_OFF, STATE_ON)
from homeassistant.setup import setup_component
from tests.common import get_test_home_assistant, mock_service


ENTITY_VACUUM_BASIC = '{}.{}'.format(DOMAIN, DEMO_VACUUM_BASIC).lower()
ENTITY_VACUUM_COMPLETE = '{}.{}'.format(DOMAIN, DEMO_VACUUM_COMPLETE).lower()
ENTITY_VACUUM_MINIMAL = '{}.{}'.format(DOMAIN, DEMO_VACUUM_MINIMAL).lower()
ENTITY_VACUUM_MOST = '{}.{}'.format(DOMAIN, DEMO_VACUUM_MOST).lower()
ENTITY_VACUUM_NONE = '{}.{}'.format(DOMAIN, DEMO_VACUUM_NONE).lower()


class TestVacuumDemo(unittest.TestCase):
    """Test the Demo vacuum."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.assertTrue(setup_component(
            self.hass, DOMAIN, {DOMAIN: {CONF_PLATFORM: 'demo'}}))

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_supported_features(self):
        """Test vacuum supported features."""
        state = self.hass.states.get(ENTITY_VACUUM_COMPLETE)
        self.assertEqual(2047, state.attributes.get(ATTR_SUPPORTED_FEATURES))
        self.assertEqual("Charging", state.attributes.get(ATTR_STATUS))
        self.assertEqual(100, state.attributes.get(ATTR_BATTERY_LEVEL))
        self.assertEqual("medium", state.attributes.get(ATTR_FAN_SPEED))
        self.assertListEqual(FAN_SPEEDS,
                             state.attributes.get(ATTR_FAN_SPEED_LIST))
        self.assertEqual(STATE_OFF, state.state)

        state = self.hass.states.get(ENTITY_VACUUM_MOST)
        self.assertEqual(219, state.attributes.get(ATTR_SUPPORTED_FEATURES))
        self.assertEqual("Charging", state.attributes.get(ATTR_STATUS))
        self.assertEqual(100, state.attributes.get(ATTR_BATTERY_LEVEL))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED_LIST))
        self.assertEqual(STATE_OFF, state.state)

        state = self.hass.states.get(ENTITY_VACUUM_BASIC)
        self.assertEqual(195, state.attributes.get(ATTR_SUPPORTED_FEATURES))
        self.assertEqual("Charging", state.attributes.get(ATTR_STATUS))
        self.assertEqual(100, state.attributes.get(ATTR_BATTERY_LEVEL))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED_LIST))
        self.assertEqual(STATE_OFF, state.state)

        state = self.hass.states.get(ENTITY_VACUUM_MINIMAL)
        self.assertEqual(3, state.attributes.get(ATTR_SUPPORTED_FEATURES))
        self.assertEqual(None, state.attributes.get(ATTR_STATUS))
        self.assertEqual(None, state.attributes.get(ATTR_BATTERY_LEVEL))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED_LIST))
        self.assertEqual(STATE_OFF, state.state)

        state = self.hass.states.get(ENTITY_VACUUM_NONE)
        self.assertEqual(0, state.attributes.get(ATTR_SUPPORTED_FEATURES))
        self.assertEqual(None, state.attributes.get(ATTR_STATUS))
        self.assertEqual(None, state.attributes.get(ATTR_BATTERY_LEVEL))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED))
        self.assertEqual(None, state.attributes.get(ATTR_FAN_SPEED_LIST))
        self.assertEqual(STATE_OFF, state.state)

    def test_methods(self):
        """Test if methods call the services as expected."""
        self.hass.states.set(ENTITY_VACUUM_BASIC, STATE_ON)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass, ENTITY_VACUUM_BASIC))

        self.hass.states.set(ENTITY_VACUUM_BASIC, STATE_OFF)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_BASIC))

        self.hass.states.set(ENTITY_ID_ALL_VACUUMS, STATE_ON)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass))

        self.hass.states.set(ENTITY_ID_ALL_VACUUMS, STATE_OFF)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass))

        vacuum.turn_on(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass, ENTITY_VACUUM_COMPLETE))

        vacuum.turn_off(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_COMPLETE))

        vacuum.toggle(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass, ENTITY_VACUUM_COMPLETE))

        vacuum.start_pause(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_COMPLETE))

        vacuum.start_pause(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass, ENTITY_VACUUM_COMPLETE))

        vacuum.stop(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_COMPLETE))

        state = self.hass.states.get(ENTITY_VACUUM_COMPLETE)
        self.assertLess(state.attributes.get(ATTR_BATTERY_LEVEL), 100)
        self.assertNotEqual("Charging", state.attributes.get(ATTR_STATUS))

        vacuum.locate(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_COMPLETE)
        self.assertIn("I'm over here", state.attributes.get(ATTR_STATUS))

        vacuum.return_to_base(self.hass, ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_COMPLETE)
        self.assertIn("Returning home", state.attributes.get(ATTR_STATUS))

        vacuum.set_fan_speed(self.hass, FAN_SPEEDS[-1],
                             entity_id=ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_COMPLETE)
        self.assertEqual(FAN_SPEEDS[-1], state.attributes.get(ATTR_FAN_SPEED))

        vacuum.clean_spot(self.hass, entity_id=ENTITY_VACUUM_COMPLETE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_COMPLETE)
        self.assertIn("spot", state.attributes.get(ATTR_STATUS))
        self.assertEqual(STATE_ON, state.state)

    def test_unsupported_methods(self):
        """Test service calls for unsupported vacuums."""
        self.hass.states.set(ENTITY_VACUUM_NONE, STATE_ON)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass, ENTITY_VACUUM_NONE))

        vacuum.turn_off(self.hass, ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass, ENTITY_VACUUM_NONE))

        vacuum.stop(self.hass, ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        self.assertTrue(vacuum.is_on(self.hass, ENTITY_VACUUM_NONE))

        self.hass.states.set(ENTITY_VACUUM_NONE, STATE_OFF)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_NONE))

        vacuum.turn_on(self.hass, ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_NONE))

        vacuum.toggle(self.hass, ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_NONE))

        # Non supported methods:
        vacuum.start_pause(self.hass, ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        self.assertFalse(vacuum.is_on(self.hass, ENTITY_VACUUM_NONE))

        vacuum.locate(self.hass, ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_NONE)
        self.assertIsNone(state.attributes.get(ATTR_STATUS))

        vacuum.return_to_base(self.hass, ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_NONE)
        self.assertIsNone(state.attributes.get(ATTR_STATUS))

        vacuum.set_fan_speed(self.hass, FAN_SPEEDS[-1],
                             entity_id=ENTITY_VACUUM_NONE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_NONE)
        self.assertNotEqual(FAN_SPEEDS[-1],
                            state.attributes.get(ATTR_FAN_SPEED))

        vacuum.clean_spot(self.hass, entity_id=ENTITY_VACUUM_BASIC)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_VACUUM_BASIC)
        self.assertNotIn("spot", state.attributes.get(ATTR_STATUS))
        self.assertEqual(STATE_OFF, state.state)

    def test_services(self):
        """Test vacuum services."""
        # Test send_command
        send_command_calls = mock_service(
            self.hass, DOMAIN, SERVICE_SEND_COMMAND)

        params = {"rotate": 150, "speed": 20}
        vacuum.send_command(
            self.hass, 'test_command', entity_id=ENTITY_VACUUM_BASIC,
            params=params)

        self.hass.block_till_done()
        self.assertEqual(1, len(send_command_calls))
        call = send_command_calls[-1]

        self.assertEqual(DOMAIN, call.domain)
        self.assertEqual(SERVICE_SEND_COMMAND, call.service)
        self.assertEqual(ENTITY_VACUUM_BASIC, call.data[ATTR_ENTITY_ID])
        self.assertEqual('test_command', call.data[ATTR_COMMAND])
        self.assertEqual(params, call.data[ATTR_PARAMS])

        # Test set fan speed
        set_fan_speed_calls = mock_service(
            self.hass, DOMAIN, SERVICE_SET_FAN_SPEED)

        vacuum.set_fan_speed(
            self.hass, FAN_SPEEDS[0], entity_id=ENTITY_VACUUM_COMPLETE)

        self.hass.block_till_done()
        self.assertEqual(1, len(set_fan_speed_calls))
        call = set_fan_speed_calls[-1]

        self.assertEqual(DOMAIN, call.domain)
        self.assertEqual(SERVICE_SET_FAN_SPEED, call.service)
        self.assertEqual(ENTITY_VACUUM_COMPLETE, call.data[ATTR_ENTITY_ID])
        self.assertEqual(FAN_SPEEDS[0], call.data[ATTR_FAN_SPEED])

    def test_set_fan_speed(self):
        """Test vacuum service to set the fan speed."""
        group_vacuums = ','.join([ENTITY_VACUUM_BASIC,
                                  ENTITY_VACUUM_COMPLETE])
        old_state_basic = self.hass.states.get(ENTITY_VACUUM_BASIC)
        old_state_complete = self.hass.states.get(ENTITY_VACUUM_COMPLETE)

        vacuum.set_fan_speed(
            self.hass, FAN_SPEEDS[0], entity_id=group_vacuums)

        self.hass.block_till_done()
        new_state_basic = self.hass.states.get(ENTITY_VACUUM_BASIC)
        new_state_complete = self.hass.states.get(ENTITY_VACUUM_COMPLETE)

        self.assertEqual(old_state_basic, new_state_basic)
        self.assertNotIn(ATTR_FAN_SPEED, new_state_basic.attributes)

        self.assertNotEqual(old_state_complete, new_state_complete)
        self.assertEqual(FAN_SPEEDS[1],
                         old_state_complete.attributes[ATTR_FAN_SPEED])
        self.assertEqual(FAN_SPEEDS[0],
                         new_state_complete.attributes[ATTR_FAN_SPEED])

    def test_send_command(self):
        """Test vacuum service to send a command."""
        group_vacuums = ','.join([ENTITY_VACUUM_BASIC,
                                  ENTITY_VACUUM_COMPLETE])
        old_state_basic = self.hass.states.get(ENTITY_VACUUM_BASIC)
        old_state_complete = self.hass.states.get(ENTITY_VACUUM_COMPLETE)

        vacuum.send_command(
            self.hass, 'test_command', params={"p1": 3},
            entity_id=group_vacuums)

        self.hass.block_till_done()
        new_state_basic = self.hass.states.get(ENTITY_VACUUM_BASIC)
        new_state_complete = self.hass.states.get(ENTITY_VACUUM_COMPLETE)

        self.assertEqual(old_state_basic, new_state_basic)
        self.assertNotEqual(old_state_complete, new_state_complete)
        self.assertEqual(STATE_ON, new_state_complete.state)
        self.assertEqual("Executing test_command({'p1': 3})",
                         new_state_complete.attributes[ATTR_STATUS])
