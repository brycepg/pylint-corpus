"""Tests for the Google Assistant traits."""
import pytest

from homeassistant.const import (
    STATE_ON, STATE_OFF, ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF,
    ATTR_UNIT_OF_MEASUREMENT, TEMP_CELSIUS, TEMP_FAHRENHEIT)
from homeassistant.core import State, DOMAIN as HA_DOMAIN
from homeassistant.components import (
    climate,
    cover,
    fan,
    input_boolean,
    light,
    media_player,
    scene,
    script,
    switch,
)
from homeassistant.components.google_assistant import trait, helpers, const
from homeassistant.util import color

from tests.common import async_mock_service


async def test_brightness_light(hass):
    """Test brightness trait support for light domain."""
    assert trait.BrightnessTrait.supported(light.DOMAIN,
                                           light.SUPPORT_BRIGHTNESS)

    trt = trait.BrightnessTrait(State('light.bla', light.STATE_ON, {
        light.ATTR_BRIGHTNESS: 243
    }))

    assert trt.sync_attributes() == {}

    assert trt.query_attributes() == {
        'brightness': 95
    }

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await trt.execute(hass, trait.COMMAND_BRIGHTNESS_ABSOLUTE, {
        'brightness': 50
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'light.bla',
        light.ATTR_BRIGHTNESS_PCT: 50
    }


async def test_brightness_cover(hass):
    """Test brightness trait support for cover domain."""
    assert trait.BrightnessTrait.supported(cover.DOMAIN,
                                           cover.SUPPORT_SET_POSITION)

    trt = trait.BrightnessTrait(State('cover.bla', cover.STATE_OPEN, {
        cover.ATTR_CURRENT_POSITION: 75
    }))

    assert trt.sync_attributes() == {}

    assert trt.query_attributes() == {
        'brightness': 75
    }

    calls = async_mock_service(
        hass, cover.DOMAIN, cover.SERVICE_SET_COVER_POSITION)
    await trt.execute(hass, trait.COMMAND_BRIGHTNESS_ABSOLUTE, {
        'brightness': 50
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'cover.bla',
        cover.ATTR_POSITION: 50
    }


async def test_brightness_media_player(hass):
    """Test brightness trait support for media player domain."""
    assert trait.BrightnessTrait.supported(media_player.DOMAIN,
                                           media_player.SUPPORT_VOLUME_SET)

    trt = trait.BrightnessTrait(State(
        'media_player.bla', media_player.STATE_PLAYING, {
            media_player.ATTR_MEDIA_VOLUME_LEVEL: .3
        }))

    assert trt.sync_attributes() == {}

    assert trt.query_attributes() == {
        'brightness': 30
    }

    calls = async_mock_service(
        hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_SET)
    await trt.execute(hass, trait.COMMAND_BRIGHTNESS_ABSOLUTE, {
        'brightness': 60
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'media_player.bla',
        media_player.ATTR_MEDIA_VOLUME_LEVEL: .6
    }


async def test_onoff_group(hass):
    """Test OnOff trait support for group domain."""
    assert trait.OnOffTrait.supported(media_player.DOMAIN, 0)

    trt_on = trait.OnOffTrait(State('group.bla', STATE_ON))

    assert trt_on.sync_attributes() == {}

    assert trt_on.query_attributes() == {
        'on': True
    }

    trt_off = trait.OnOffTrait(State('group.bla', STATE_OFF))
    assert trt_off.query_attributes() == {
        'on': False
    }

    on_calls = async_mock_service(hass, HA_DOMAIN, SERVICE_TURN_ON)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': True
    })
    assert len(on_calls) == 1
    assert on_calls[0].data == {
        ATTR_ENTITY_ID: 'group.bla',
    }

    off_calls = async_mock_service(hass, HA_DOMAIN, SERVICE_TURN_OFF)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': False
    })
    assert len(off_calls) == 1
    assert off_calls[0].data == {
        ATTR_ENTITY_ID: 'group.bla',
    }


async def test_onoff_input_boolean(hass):
    """Test OnOff trait support for input_boolean domain."""
    assert trait.OnOffTrait.supported(media_player.DOMAIN, 0)

    trt_on = trait.OnOffTrait(State('input_boolean.bla', STATE_ON))

    assert trt_on.sync_attributes() == {}

    assert trt_on.query_attributes() == {
        'on': True
    }

    trt_off = trait.OnOffTrait(State('input_boolean.bla', STATE_OFF))
    assert trt_off.query_attributes() == {
        'on': False
    }

    on_calls = async_mock_service(hass, input_boolean.DOMAIN, SERVICE_TURN_ON)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': True
    })
    assert len(on_calls) == 1
    assert on_calls[0].data == {
        ATTR_ENTITY_ID: 'input_boolean.bla',
    }

    off_calls = async_mock_service(hass, input_boolean.DOMAIN,
                                   SERVICE_TURN_OFF)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': False
    })
    assert len(off_calls) == 1
    assert off_calls[0].data == {
        ATTR_ENTITY_ID: 'input_boolean.bla',
    }


async def test_onoff_switch(hass):
    """Test OnOff trait support for switch domain."""
    assert trait.OnOffTrait.supported(media_player.DOMAIN, 0)

    trt_on = trait.OnOffTrait(State('switch.bla', STATE_ON))

    assert trt_on.sync_attributes() == {}

    assert trt_on.query_attributes() == {
        'on': True
    }

    trt_off = trait.OnOffTrait(State('switch.bla', STATE_OFF))
    assert trt_off.query_attributes() == {
        'on': False
    }

    on_calls = async_mock_service(hass, switch.DOMAIN, SERVICE_TURN_ON)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': True
    })
    assert len(on_calls) == 1
    assert on_calls[0].data == {
        ATTR_ENTITY_ID: 'switch.bla',
    }

    off_calls = async_mock_service(hass, switch.DOMAIN, SERVICE_TURN_OFF)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': False
    })
    assert len(off_calls) == 1
    assert off_calls[0].data == {
        ATTR_ENTITY_ID: 'switch.bla',
    }


async def test_onoff_fan(hass):
    """Test OnOff trait support for fan domain."""
    assert trait.OnOffTrait.supported(media_player.DOMAIN, 0)

    trt_on = trait.OnOffTrait(State('fan.bla', STATE_ON))

    assert trt_on.sync_attributes() == {}

    assert trt_on.query_attributes() == {
        'on': True
    }

    trt_off = trait.OnOffTrait(State('fan.bla', STATE_OFF))
    assert trt_off.query_attributes() == {
        'on': False
    }

    on_calls = async_mock_service(hass, fan.DOMAIN, SERVICE_TURN_ON)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': True
    })
    assert len(on_calls) == 1
    assert on_calls[0].data == {
        ATTR_ENTITY_ID: 'fan.bla',
    }

    off_calls = async_mock_service(hass, fan.DOMAIN, SERVICE_TURN_OFF)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': False
    })
    assert len(off_calls) == 1
    assert off_calls[0].data == {
        ATTR_ENTITY_ID: 'fan.bla',
    }


async def test_onoff_light(hass):
    """Test OnOff trait support for light domain."""
    assert trait.OnOffTrait.supported(media_player.DOMAIN, 0)

    trt_on = trait.OnOffTrait(State('light.bla', STATE_ON))

    assert trt_on.sync_attributes() == {}

    assert trt_on.query_attributes() == {
        'on': True
    }

    trt_off = trait.OnOffTrait(State('light.bla', STATE_OFF))
    assert trt_off.query_attributes() == {
        'on': False
    }

    on_calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': True
    })
    assert len(on_calls) == 1
    assert on_calls[0].data == {
        ATTR_ENTITY_ID: 'light.bla',
    }

    off_calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_OFF)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': False
    })
    assert len(off_calls) == 1
    assert off_calls[0].data == {
        ATTR_ENTITY_ID: 'light.bla',
    }


async def test_onoff_cover(hass):
    """Test OnOff trait support for cover domain."""
    assert trait.OnOffTrait.supported(media_player.DOMAIN, 0)

    trt_on = trait.OnOffTrait(State('cover.bla', cover.STATE_OPEN))

    assert trt_on.sync_attributes() == {}

    assert trt_on.query_attributes() == {
        'on': True
    }

    trt_off = trait.OnOffTrait(State('cover.bla', cover.STATE_CLOSED))
    assert trt_off.query_attributes() == {
        'on': False
    }

    on_calls = async_mock_service(hass, cover.DOMAIN, cover.SERVICE_OPEN_COVER)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': True
    })
    assert len(on_calls) == 1
    assert on_calls[0].data == {
        ATTR_ENTITY_ID: 'cover.bla',
    }

    off_calls = async_mock_service(hass, cover.DOMAIN,
                                   cover.SERVICE_CLOSE_COVER)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': False
    })
    assert len(off_calls) == 1
    assert off_calls[0].data == {
        ATTR_ENTITY_ID: 'cover.bla',
    }


async def test_onoff_media_player(hass):
    """Test OnOff trait support for media_player domain."""
    assert trait.OnOffTrait.supported(media_player.DOMAIN, 0)

    trt_on = trait.OnOffTrait(State('media_player.bla', STATE_ON))

    assert trt_on.sync_attributes() == {}

    assert trt_on.query_attributes() == {
        'on': True
    }

    trt_off = trait.OnOffTrait(State('media_player.bla', STATE_OFF))
    assert trt_off.query_attributes() == {
        'on': False
    }

    on_calls = async_mock_service(hass, media_player.DOMAIN, SERVICE_TURN_ON)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': True
    })
    assert len(on_calls) == 1
    assert on_calls[0].data == {
        ATTR_ENTITY_ID: 'media_player.bla',
    }

    off_calls = async_mock_service(hass, media_player.DOMAIN, SERVICE_TURN_OFF)
    await trt_on.execute(hass, trait.COMMAND_ONOFF, {
        'on': False
    })
    assert len(off_calls) == 1
    assert off_calls[0].data == {
        ATTR_ENTITY_ID: 'media_player.bla',
    }


async def test_color_spectrum_light(hass):
    """Test ColorSpectrum trait support for light domain."""
    assert not trait.ColorSpectrumTrait.supported(light.DOMAIN, 0)
    assert trait.ColorSpectrumTrait.supported(light.DOMAIN,
                                              light.SUPPORT_RGB_COLOR)
    assert trait.ColorSpectrumTrait.supported(light.DOMAIN,
                                              light.SUPPORT_XY_COLOR)

    trt = trait.ColorSpectrumTrait(State('light.bla', STATE_ON, {
        light.ATTR_RGB_COLOR: [255, 10, 10]
    }))

    assert trt.sync_attributes() == {
        'colorModel': 'rgb'
    }

    assert trt.query_attributes() == {
        'color': {
            'spectrumRGB': 16714250
        }
    }

    assert not trt.can_execute(trait.COMMAND_COLOR_ABSOLUTE, {
        'color': {
            'temperature': 400
        }
    })
    assert trt.can_execute(trait.COMMAND_COLOR_ABSOLUTE, {
        'color': {
            'spectrumRGB': 16715792
        }
    })

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await trt.execute(hass, trait.COMMAND_COLOR_ABSOLUTE, {
        'color': {
            'spectrumRGB': 1052927
        }
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'light.bla',
        light.ATTR_RGB_COLOR: [16, 16, 255]
    }


async def test_color_temperature_light(hass):
    """Test ColorTemperature trait support for light domain."""
    assert not trait.ColorTemperatureTrait.supported(light.DOMAIN, 0)
    assert trait.ColorTemperatureTrait.supported(light.DOMAIN,
                                                 light.SUPPORT_COLOR_TEMP)

    trt = trait.ColorTemperatureTrait(State('light.bla', STATE_ON, {
        light.ATTR_MIN_MIREDS: 200,
        light.ATTR_COLOR_TEMP: 300,
        light.ATTR_MAX_MIREDS: 500,
    }))

    assert trt.sync_attributes() == {
        'temperatureMinK': 5000,
        'temperatureMaxK': 2000,
    }

    assert trt.query_attributes() == {
        'color': {
            'temperature': 3333
        }
    }

    assert trt.can_execute(trait.COMMAND_COLOR_ABSOLUTE, {
        'color': {
            'temperature': 400
        }
    })
    assert not trt.can_execute(trait.COMMAND_COLOR_ABSOLUTE, {
        'color': {
            'spectrumRGB': 16715792
        }
    })

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)

    with pytest.raises(helpers.SmartHomeError) as err:
        await trt.execute(hass, trait.COMMAND_COLOR_ABSOLUTE, {
            'color': {
                'temperature': 5555
            }
        })
    assert err.value.code == const.ERR_VALUE_OUT_OF_RANGE

    await trt.execute(hass, trait.COMMAND_COLOR_ABSOLUTE, {
        'color': {
            'temperature': 2857
        }
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'light.bla',
        light.ATTR_COLOR_TEMP: color.color_temperature_kelvin_to_mired(2857)
    }


async def test_scene_scene(hass):
    """Test Scene trait support for scene domain."""
    assert trait.SceneTrait.supported(scene.DOMAIN, 0)

    trt = trait.SceneTrait(State('scene.bla', scene.STATE))
    assert trt.sync_attributes() == {}
    assert trt.query_attributes() == {}
    assert trt.can_execute(trait.COMMAND_ACTIVATE_SCENE, {})

    calls = async_mock_service(hass, scene.DOMAIN, SERVICE_TURN_ON)
    await trt.execute(hass, trait.COMMAND_ACTIVATE_SCENE, {})
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'scene.bla',
    }


async def test_scene_script(hass):
    """Test Scene trait support for script domain."""
    assert trait.SceneTrait.supported(script.DOMAIN, 0)

    trt = trait.SceneTrait(State('script.bla', STATE_OFF))
    assert trt.sync_attributes() == {}
    assert trt.query_attributes() == {}
    assert trt.can_execute(trait.COMMAND_ACTIVATE_SCENE, {})

    calls = async_mock_service(hass, script.DOMAIN, SERVICE_TURN_ON)
    await trt.execute(hass, trait.COMMAND_ACTIVATE_SCENE, {})

    # We don't wait till script execution is done.
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'script.bla',
    }


async def test_temperature_setting_climate_range(hass):
    """Test TemperatureSetting trait support for climate domain - range."""
    assert not trait.TemperatureSettingTrait.supported(climate.DOMAIN, 0)
    assert trait.TemperatureSettingTrait.supported(
        climate.DOMAIN, climate.SUPPORT_OPERATION_MODE)

    trt = trait.TemperatureSettingTrait(State(
        'climate.bla', climate.STATE_AUTO, {
            climate.ATTR_CURRENT_TEMPERATURE: 70,
            climate.ATTR_CURRENT_HUMIDITY: 25,
            climate.ATTR_OPERATION_MODE: climate.STATE_AUTO,
            climate.ATTR_OPERATION_LIST: [
                climate.STATE_OFF,
                climate.STATE_COOL,
                climate.STATE_HEAT,
                climate.STATE_AUTO,
            ],
            climate.ATTR_TARGET_TEMP_HIGH: 75,
            climate.ATTR_TARGET_TEMP_LOW: 65,
            climate.ATTR_MIN_TEMP: 50,
            climate.ATTR_MAX_TEMP: 80,
            ATTR_UNIT_OF_MEASUREMENT: TEMP_FAHRENHEIT,
        }))
    assert trt.sync_attributes() == {
        'availableThermostatModes': 'off,cool,heat,heatcool',
        'thermostatTemperatureUnit': 'F',
    }
    assert trt.query_attributes() == {
        'thermostatMode': 'heatcool',
        'thermostatTemperatureAmbient': 21.1,
        'thermostatHumidityAmbient': 25,
        'thermostatTemperatureSetpointLow': 18.3,
        'thermostatTemperatureSetpointHigh': 23.9,
    }
    assert trt.can_execute(trait.COMMAND_THERMOSTAT_TEMPERATURE_SETPOINT, {})
    assert trt.can_execute(trait.COMMAND_THERMOSTAT_TEMPERATURE_SET_RANGE, {})
    assert trt.can_execute(trait.COMMAND_THERMOSTAT_SET_MODE, {})

    calls = async_mock_service(
        hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await trt.execute(hass, trait.COMMAND_THERMOSTAT_TEMPERATURE_SET_RANGE, {
        'thermostatTemperatureSetpointHigh': 25,
        'thermostatTemperatureSetpointLow': 20,
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'climate.bla',
        climate.ATTR_TARGET_TEMP_HIGH: 77,
        climate.ATTR_TARGET_TEMP_LOW: 68,
    }

    calls = async_mock_service(
        hass, climate.DOMAIN, climate.SERVICE_SET_OPERATION_MODE)
    await trt.execute(hass, trait.COMMAND_THERMOSTAT_SET_MODE, {
        'thermostatMode': 'heatcool',
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'climate.bla',
        climate.ATTR_OPERATION_MODE: climate.STATE_AUTO,
    }

    with pytest.raises(helpers.SmartHomeError) as err:
        await trt.execute(
            hass, trait.COMMAND_THERMOSTAT_TEMPERATURE_SETPOINT, {
                'thermostatTemperatureSetpoint': -100,
            })
    assert err.value.code == const.ERR_VALUE_OUT_OF_RANGE


async def test_temperature_setting_climate_setpoint(hass):
    """Test TemperatureSetting trait support for climate domain - setpoint."""
    assert not trait.TemperatureSettingTrait.supported(climate.DOMAIN, 0)
    assert trait.TemperatureSettingTrait.supported(
        climate.DOMAIN, climate.SUPPORT_OPERATION_MODE)

    trt = trait.TemperatureSettingTrait(State(
        'climate.bla', climate.STATE_AUTO, {
            climate.ATTR_OPERATION_MODE: climate.STATE_COOL,
            climate.ATTR_OPERATION_LIST: [
                climate.STATE_OFF,
                climate.STATE_COOL,
            ],
            climate.ATTR_MIN_TEMP: 10,
            climate.ATTR_MAX_TEMP: 30,
            climate.ATTR_TEMPERATURE: 18,
            climate.ATTR_CURRENT_TEMPERATURE: 20,
            ATTR_UNIT_OF_MEASUREMENT: TEMP_CELSIUS,
        }))
    assert trt.sync_attributes() == {
        'availableThermostatModes': 'off,cool',
        'thermostatTemperatureUnit': 'C',
    }
    assert trt.query_attributes() == {
        'thermostatMode': 'cool',
        'thermostatTemperatureAmbient': 20,
        'thermostatTemperatureSetpoint': 18,
    }
    assert trt.can_execute(trait.COMMAND_THERMOSTAT_TEMPERATURE_SETPOINT, {})
    assert trt.can_execute(trait.COMMAND_THERMOSTAT_TEMPERATURE_SET_RANGE, {})
    assert trt.can_execute(trait.COMMAND_THERMOSTAT_SET_MODE, {})

    calls = async_mock_service(
        hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)

    with pytest.raises(helpers.SmartHomeError):
        await trt.execute(
            hass, trait.COMMAND_THERMOSTAT_TEMPERATURE_SETPOINT, {
                'thermostatTemperatureSetpoint': -100,
            })

    await trt.execute(hass, trait.COMMAND_THERMOSTAT_TEMPERATURE_SETPOINT, {
        'thermostatTemperatureSetpoint': 19,
    })
    assert len(calls) == 1
    assert calls[0].data == {
        ATTR_ENTITY_ID: 'climate.bla',
        climate.ATTR_TEMPERATURE: 19
    }
