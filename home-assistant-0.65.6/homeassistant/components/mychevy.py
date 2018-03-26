"""
MyChevy Component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/mychevy/
"""
from datetime import timedelta
import logging
import threading
import time

import voluptuous as vol

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.util import Throttle

REQUIREMENTS = ["mychevy==0.1.1"]

DOMAIN = 'mychevy'
UPDATE_TOPIC = DOMAIN
ERROR_TOPIC = DOMAIN + "_error"

MYCHEVY_SUCCESS = "success"
MYCHEVY_ERROR = "error"

NOTIFICATION_ID = 'mychevy_website_notification'
NOTIFICATION_TITLE = 'MyChevy website status'

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)
ERROR_SLEEP_TIME = timedelta(minutes=30)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


class EVSensorConfig(object):
    """The EV sensor configuration."""

    def __init__(self, name, attr, unit_of_measurement=None, icon=None):
        """Create new sensor configuration."""
        self.name = name
        self.attr = attr
        self.unit_of_measurement = unit_of_measurement
        self.icon = icon


class EVBinarySensorConfig(object):
    """The EV binary sensor configuration."""

    def __init__(self, name, attr, device_class=None):
        """Create new binary sensor configuration."""
        self.name = name
        self.attr = attr
        self.device_class = device_class


def setup(hass, base_config):
    """Set up the mychevy component."""
    import mychevy.mychevy as mc

    config = base_config.get(DOMAIN)

    email = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    hass.data[DOMAIN] = MyChevyHub(mc.MyChevy(email, password), hass)
    hass.data[DOMAIN].start()

    discovery.load_platform(hass, 'sensor', DOMAIN, {}, config)
    discovery.load_platform(hass, 'binary_sensor', DOMAIN, {}, config)

    return True


class MyChevyHub(threading.Thread):
    """MyChevy Hub.

    Connecting to the mychevy website is done through a selenium
    webscraping process. That can only run synchronously. In order to
    prevent blocking of other parts of Home Assistant the architecture
    launches a polling loop in a thread.

    When new data is received, sensors are updated, and hass is
    signaled that there are updates. Sensors are not created until the
    first update, which will be 60 - 120 seconds after the platform
    starts.
    """

    def __init__(self, client, hass):
        """Initialize MyChevy Hub."""
        super().__init__()
        self._client = client
        self.hass = hass
        self.car = None
        self.status = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update sensors from mychevy website.

        This is a synchronous polling call that takes a very long time
        (like 2 to 3 minutes long time)

        """
        self.car = self._client.data()

    def run(self):
        """Thread run loop."""
        # We add the status device first outside of the loop

        # And then busy wait on threads
        while True:
            try:
                _LOGGER.info("Starting mychevy loop")
                self.update()
                self.hass.helpers.dispatcher.dispatcher_send(UPDATE_TOPIC)
                time.sleep(MIN_TIME_BETWEEN_UPDATES.seconds)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Error updating mychevy data. "
                    "This probably means the OnStar link is down again")
                self.hass.helpers.dispatcher.dispatcher_send(ERROR_TOPIC)
                time.sleep(ERROR_SLEEP_TIME.seconds)
