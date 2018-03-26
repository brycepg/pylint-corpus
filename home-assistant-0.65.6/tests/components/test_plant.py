"""Unit tests for platform/plant.py."""
import asyncio
import unittest
import pytest
from datetime import datetime, timedelta

from homeassistant.const import (ATTR_UNIT_OF_MEASUREMENT, STATE_UNKNOWN,
                                 STATE_PROBLEM, STATE_OK)
from homeassistant.components import recorder
import homeassistant.components.plant as plant
from homeassistant.setup import setup_component

from tests.common import get_test_home_assistant, init_recorder_component


GOOD_DATA = {
    'moisture': 50,
    'battery': 90,
    'temperature': 23.4,
    'conductivity': 777,
    'brightness': 987,
}

BRIGHTNESS_ENTITY = 'sensor.mqtt_plant_brightness'
MOISTURE_ENTITY = 'sensor.mqtt_plant_moisture'

GOOD_CONFIG = {
    'sensors': {
        'moisture': MOISTURE_ENTITY,
        'battery': 'sensor.mqtt_plant_battery',
        'temperature': 'sensor.mqtt_plant_temperature',
        'conductivity': 'sensor.mqtt_plant_conductivity',
        'brightness': BRIGHTNESS_ENTITY,
    },
    'min_moisture': 20,
    'max_moisture': 60,
    'min_battery': 17,
    'min_conductivity': 500,
    'min_temperature': 15,
    'min_brightness': 500,
}


class _MockState(object):

    def __init__(self, state=None):
        self.state = state


class TestPlant(unittest.TestCase):
    """Tests for component "plant"."""

    def setUp(self):
        """Create test instance of home assistant."""
        self.hass = get_test_home_assistant()
        self.hass.start()

    def tearDown(self):
        """Stop everything that was started."""
        self.hass.stop()

    @asyncio.coroutine
    def test_valid_data(self):
        """Test processing valid data."""
        sensor = plant.Plant('my plant', GOOD_CONFIG)
        sensor.hass = self.hass
        for reading, value in GOOD_DATA.items():
            sensor.state_changed(
                GOOD_CONFIG['sensors'][reading], None,
                _MockState(value))
        assert sensor.state == 'ok'
        attrib = sensor.state_attributes
        for reading, value in GOOD_DATA.items():
            # battery level has a different name in
            # the JSON format than in hass
            assert attrib[reading] == value

    @asyncio.coroutine
    def test_low_battery(self):
        """Test processing with low battery data and limit set."""
        sensor = plant.Plant('other plant', GOOD_CONFIG)
        sensor.hass = self.hass
        assert sensor.state_attributes['problem'] == 'none'
        sensor.state_changed('sensor.mqtt_plant_battery',
                             _MockState(45), _MockState(10))
        assert sensor.state == 'problem'
        assert sensor.state_attributes['problem'] == 'battery low'

    def test_update_states(self):
        """Test updating the state of a sensor.

        Make sure that plant processes this correctly.
        """
        plant_name = 'some_plant'
        assert setup_component(self.hass, plant.DOMAIN, {
            plant.DOMAIN: {
                plant_name: GOOD_CONFIG
            }
        })
        self.hass.states.set(MOISTURE_ENTITY, 5,
                             {ATTR_UNIT_OF_MEASUREMENT: 'us/cm'})
        self.hass.block_till_done()
        state = self.hass.states.get('plant.'+plant_name)
        self.assertEqual(STATE_PROBLEM, state.state)
        self.assertEqual(5, state.attributes[plant.READING_MOISTURE])

    @pytest.mark.skipif(plant.ENABLE_LOAD_HISTORY is False,
                        reason="tests for loading from DB are unstable, thus"
                               "this feature is turned of until tests become"
                               "stable")
    def test_load_from_db(self):
        """Test bootstrapping the brightness history from the database.

        This test can should only be executed if the loading of the history
        is enabled via plant.ENABLE_LOAD_HISTORY.
        """
        init_recorder_component(self.hass)
        plant_name = 'wise_plant'
        for value in [20, 30, 10]:

            self.hass.states.set(BRIGHTNESS_ENTITY, value,
                                 {ATTR_UNIT_OF_MEASUREMENT: 'Lux'})
            self.hass.block_till_done()
        # wait for the recorder to really store the data
        self.hass.data[recorder.DATA_INSTANCE].block_till_done()

        assert setup_component(self.hass, plant.DOMAIN, {
            plant.DOMAIN: {
                plant_name: GOOD_CONFIG
            }
        })
        self.hass.block_till_done()

        state = self.hass.states.get('plant.'+plant_name)
        self.assertEqual(STATE_UNKNOWN, state.state)
        max_brightness = state.attributes.get(
            plant.ATTR_MAX_BRIGHTNESS_HISTORY)
        self.assertEqual(30, max_brightness)

    def test_brightness_history(self):
        """Test the min_brightness check."""
        plant_name = 'some_plant'
        assert setup_component(self.hass, plant.DOMAIN, {
            plant.DOMAIN: {
                plant_name: GOOD_CONFIG
            }
        })
        self.hass.states.set(BRIGHTNESS_ENTITY, 100,
                             {ATTR_UNIT_OF_MEASUREMENT: 'lux'})
        self.hass.block_till_done()
        state = self.hass.states.get('plant.'+plant_name)
        self.assertEqual(STATE_PROBLEM, state.state)

        self.hass.states.set(BRIGHTNESS_ENTITY, 600,
                             {ATTR_UNIT_OF_MEASUREMENT: 'lux'})
        self.hass.block_till_done()
        state = self.hass.states.get('plant.'+plant_name)
        self.assertEqual(STATE_OK, state.state)

        self.hass.states.set(BRIGHTNESS_ENTITY, 100,
                             {ATTR_UNIT_OF_MEASUREMENT: 'lux'})
        self.hass.block_till_done()
        state = self.hass.states.get('plant.'+plant_name)
        self.assertEqual(STATE_OK, state.state)


class TestDailyHistory(unittest.TestCase):
    """Test the DailyHistory helper class."""

    def test_no_data(self):
        """Test with empty history."""
        dh = plant.DailyHistory(3)
        self.assertIsNone(dh.max)

    def test_one_day(self):
        """Test storing data for the same day."""
        dh = plant.DailyHistory(3)
        values = [-2, 10, 0, 5, 20]
        for i in range(len(values)):
            dh.add_measurement(values[i])
            max_value = max(values[0:i+1])
            self.assertEqual(1, len(dh._days))
            self.assertEqual(dh.max, max_value)

    def test_multiple_days(self):
        """Test storing data for different days."""
        dh = plant.DailyHistory(3)
        today = datetime.now()
        today_minus_1 = today - timedelta(days=1)
        today_minus_2 = today_minus_1 - timedelta(days=1)
        today_minus_3 = today_minus_2 - timedelta(days=1)
        days = [today_minus_3, today_minus_2, today_minus_1, today]
        values = [10, 1, 7, 3]
        max_values = [10, 10, 10, 7]

        for i in range(len(days)):
            dh.add_measurement(values[i], days[i])
            self.assertEqual(max_values[i], dh.max)
