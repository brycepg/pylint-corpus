"""
Support for ADS light sources.

For more details about this platform, please refer to the documentation.
https://home-assistant.io/components/light.ads/

"""
import asyncio
import logging
import voluptuous as vol
from homeassistant.components.light import Light, ATTR_BRIGHTNESS, \
    SUPPORT_BRIGHTNESS, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.components.ads import DATA_ADS, CONF_ADS_VAR, \
    CONF_ADS_VAR_BRIGHTNESS
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ['ads']
DEFAULT_NAME = 'ADS Light'
CONF_ADSVAR_BRIGHTNESS = 'adsvar_brightness'
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ADS_VAR): cv.string,
    vol.Optional(CONF_ADS_VAR_BRIGHTNESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the light platform for ADS."""
    ads_hub = hass.data.get(DATA_ADS)

    ads_var_enable = config.get(CONF_ADS_VAR)
    ads_var_brightness = config.get(CONF_ADS_VAR_BRIGHTNESS)
    name = config.get(CONF_NAME)

    add_devices([AdsLight(ads_hub, ads_var_enable, ads_var_brightness,
                          name)], True)


class AdsLight(Light):
    """Representation of ADS light."""

    def __init__(self, ads_hub, ads_var_enable, ads_var_brightness, name):
        """Initialize AdsLight entity."""
        self._ads_hub = ads_hub
        self._on_state = False
        self._brightness = None
        self._name = name
        self.ads_var_enable = ads_var_enable
        self.ads_var_brightness = ads_var_brightness

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register device notification."""
        def update_on_state(name, value):
            """Handle device notifications for state."""
            _LOGGER.debug('Variable %s changed its value to %d', name, value)
            self._on_state = value
            self.schedule_update_ha_state()

        def update_brightness(name, value):
            """Handle device notification for brightness."""
            _LOGGER.debug('Variable %s changed its value to %d', name, value)
            self._brightness = value
            self.schedule_update_ha_state()

        self.hass.async_add_job(
            self._ads_hub.add_device_notification,
            self.ads_var_enable, self._ads_hub.PLCTYPE_BOOL, update_on_state
        )
        self.hass.async_add_job(
            self._ads_hub.add_device_notification,
            self.ads_var_brightness, self._ads_hub.PLCTYPE_INT,
            update_brightness
        )

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light (0..255)."""
        return self._brightness

    @property
    def is_on(self):
        """Return if light is on."""
        return self._on_state

    @property
    def should_poll(self):
        """Return False because entity pushes its state to HA."""
        return False

    @property
    def supported_features(self):
        """Flag supported features."""
        if self.ads_var_brightness is not None:
            return SUPPORT_BRIGHTNESS

    def turn_on(self, **kwargs):
        """Turn the light on or set a specific dimmer value."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        self._ads_hub.write_by_name(self.ads_var_enable, True,
                                    self._ads_hub.PLCTYPE_BOOL)

        if self.ads_var_brightness is not None and brightness is not None:
            self._ads_hub.write_by_name(self.ads_var_brightness, brightness,
                                        self._ads_hub.PLCTYPE_UINT)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self._ads_hub.write_by_name(self.ads_var_enable, False,
                                    self._ads_hub.PLCTYPE_BOOL)
