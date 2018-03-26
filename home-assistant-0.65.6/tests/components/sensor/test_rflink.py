"""Test for RFlink sensor components.

Test setup of rflink sensor component/platform. Verify manual and
automatic sensor creation.

"""

import asyncio

from ..test_rflink import mock_rflink

DOMAIN = 'sensor'

CONFIG = {
    'rflink': {
        'port': '/dev/ttyABC0',
        'ignore_devices': ['ignore_wildcard_*', 'ignore_sensor'],
    },
    DOMAIN: {
        'platform': 'rflink',
        'devices': {
            'test': {
                'name': 'test',
                'sensor_type': 'temperature',
            },
        },
    },
}


@asyncio.coroutine
def test_default_setup(hass, monkeypatch):
    """Test all basic functionality of the rflink sensor component."""
    # setup mocking rflink module
    event_callback, create, _, _ = yield from mock_rflink(
        hass, CONFIG, DOMAIN, monkeypatch)

    # make sure arguments are passed
    assert create.call_args_list[0][1]['ignore']

    # test default state of sensor loaded from config
    config_sensor = hass.states.get('sensor.test')
    assert config_sensor
    assert config_sensor.state == 'unknown'
    assert config_sensor.attributes['unit_of_measurement'] == '°C'

    # test event for config sensor
    event_callback({
        'id': 'test',
        'sensor': 'temperature',
        'value': 1,
        'unit': '°C',
    })
    yield from hass.async_block_till_done()

    assert hass.states.get('sensor.test').state == '1'

    # test event for new unconfigured sensor
    event_callback({
        'id': 'test2',
        'sensor': 'temperature',
        'value': 0,
        'unit': '°C',
    })
    yield from hass.async_block_till_done()

    # test  state of new sensor
    new_sensor = hass.states.get('sensor.test2')
    assert new_sensor
    assert new_sensor.state == '0'
    assert new_sensor.attributes['unit_of_measurement'] == '°C'
    assert new_sensor.attributes['icon'] == 'mdi:thermometer'


@asyncio.coroutine
def test_disable_automatic_add(hass, monkeypatch):
    """If disabled new devices should not be automatically added."""
    config = {
        'rflink': {
            'port': '/dev/ttyABC0',
        },
        DOMAIN: {
            'platform': 'rflink',
            'automatic_add': False,
        },
    }

    # setup mocking rflink module
    event_callback, _, _, _ = yield from mock_rflink(
        hass, config, DOMAIN, monkeypatch)

    # test event for new unconfigured sensor
    event_callback({
        'id': 'test2',
        'sensor': 'temperature',
        'value': 0,
        'unit': '°C',
    })
    yield from hass.async_block_till_done()

    # make sure new device is not added
    assert not hass.states.get('sensor.test2')
