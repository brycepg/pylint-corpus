"""The tests for the demo remote component."""
# pylint: disable=protected-access
import unittest

from homeassistant.setup import setup_component
import homeassistant.components.remote as remote
from homeassistant.const import STATE_ON, STATE_OFF
from tests.common import get_test_home_assistant

ENTITY_ID = 'remote.remote_one'


class TestDemoRemote(unittest.TestCase):
    """Test the demo remote."""

    # pylint: disable=invalid-name
    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.assertTrue(setup_component(self.hass, remote.DOMAIN, {'remote': {
            'platform': 'demo',
        }}))

    # pylint: disable=invalid-name
    def tearDown(self):
        """Stop down everything that was started."""
        self.hass.stop()

    def test_methods(self):
        """Test if services call the entity methods as expected."""
        remote.turn_on(self.hass, entity_id=ENTITY_ID)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_ID)
        self.assertEqual(state.state, STATE_ON)

        remote.turn_off(self.hass, entity_id=ENTITY_ID)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_ID)
        self.assertEqual(state.state, STATE_OFF)

        remote.turn_on(self.hass, entity_id=ENTITY_ID)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_ID)
        self.assertEqual(state.state, STATE_ON)

        remote.send_command(self.hass, 'test', entity_id=ENTITY_ID)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_ID)
        self.assertEqual(
            state.attributes,
            {'friendly_name': 'Remote One', 'last_command_sent': 'test'})
