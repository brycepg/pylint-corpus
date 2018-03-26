"""
Integration with the Rachio Iro sprinkler system controller.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.rachio/
"""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchDevice
from homeassistant.const import CONF_ACCESS_TOKEN
import homeassistant.helpers.config_validation as cv
import homeassistant.util as util

REQUIREMENTS = ['rachiopy==0.1.2']

_LOGGER = logging.getLogger(__name__)

CONF_MANUAL_RUN_MINS = 'manual_run_mins'

DATA_RACHIO = 'rachio'

DEFAULT_MANUAL_RUN_MINS = 10

MIN_UPDATE_INTERVAL = timedelta(seconds=30)
MIN_FORCED_UPDATE_INTERVAL = timedelta(seconds=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ACCESS_TOKEN): cv.string,
    vol.Optional(CONF_MANUAL_RUN_MINS, default=DEFAULT_MANUAL_RUN_MINS):
        cv.positive_int,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Rachio switches."""
    from rachiopy import Rachio

    # Get options
    manual_run_mins = config.get(CONF_MANUAL_RUN_MINS)
    _LOGGER.debug("Rachio run time is %d min", manual_run_mins)

    access_token = config.get(CONF_ACCESS_TOKEN)

    # Configure API
    _LOGGER.debug("Configuring Rachio API")
    rachio = Rachio(access_token)

    person = None
    try:
        person = _get_person(rachio)
    except KeyError:
        _LOGGER.error(
            "Could not reach the Rachio API. Is your access token valid?")
        return

    # Get and persist devices
    devices = _list_devices(rachio, manual_run_mins)
    if not devices:
        _LOGGER.error(
            "No Rachio devices found in account %s", person['username'])
        return

    hass.data[DATA_RACHIO] = devices[0]

    if len(devices) > 1:
        _LOGGER.warning("Multiple Rachio devices found in account, "
                        "using %s", hass.data[DATA_RACHIO].device_id)
    else:
        _LOGGER.debug("Found Rachio device")

    hass.data[DATA_RACHIO].update()
    add_devices(hass.data[DATA_RACHIO].list_zones())


def _get_person(rachio):
    """Pull the account info of the person whose access token was provided."""
    person_id = rachio.person.getInfo()[1]['id']
    return rachio.person.get(person_id)[1]


def _list_devices(rachio, manual_run_mins):
    """Pull a list of devices on the account."""
    return [RachioIro(rachio, d['id'], manual_run_mins)
            for d in _get_person(rachio)['devices']]


class RachioIro(object):
    """Representation of a Rachio Iro."""

    def __init__(self, rachio, device_id, manual_run_mins):
        """Initialize a Rachio device."""
        self.rachio = rachio
        self._device_id = device_id
        self.manual_run_mins = manual_run_mins
        self._device = None
        self._running = None
        self._zones = None

    def __str__(self):
        """Display the device as a string."""
        return "Rachio Iro {}".format(self.serial_number)

    @property
    def device_id(self):
        """Return the Rachio API device ID."""
        return self._device['id']

    @property
    def status(self):
        """Return the current status of the device."""
        return self._device['status']

    @property
    def serial_number(self):
        """Return the serial number of the device."""
        return self._device['serialNumber']

    @property
    def is_paused(self):
        """Return whether the device is temporarily disabled."""
        return self._device['paused']

    @property
    def is_on(self):
        """Return whether the device is powered on and connected."""
        return self._device['on']

    @property
    def current_schedule(self):
        """Return the schedule that the device is running right now."""
        return self._running

    def list_zones(self, include_disabled=False):
        """Return a list of the zones connected to the device, incl. data."""
        if not self._zones:
            self._zones = [RachioZone(self.rachio, self, zone['id'],
                                      self.manual_run_mins)
                           for zone in self._device['zones']]

        if include_disabled:
            return self._zones

        self.update(no_throttle=True)
        return [z for z in self._zones if z.is_enabled]

    @util.Throttle(MIN_UPDATE_INTERVAL, MIN_FORCED_UPDATE_INTERVAL)
    def update(self, **kwargs):
        """Pull updated device info from the Rachio API."""
        self._device = self.rachio.device.get(self._device_id)[1]
        self._running = self.rachio.device\
                            .getCurrentSchedule(self._device_id)[1]

        # Possibly update all zones
        for zone in self.list_zones(include_disabled=True):
            zone.update()

        _LOGGER.debug("Updated %s", str(self))


class RachioZone(SwitchDevice):
    """Representation of one zone of sprinklers connected to the Rachio Iro."""

    def __init__(self, rachio, device, zone_id, manual_run_mins):
        """Initialize a new Rachio Zone."""
        self.rachio = rachio
        self._device = device
        self._zone_id = zone_id
        self._zone = None
        self._manual_run_secs = manual_run_mins * 60

    def __str__(self):
        """Display the zone as a string."""
        return "Rachio Zone {}".format(self.name)

    @property
    def zone_id(self):
        """How the Rachio API refers to the zone."""
        return self._zone['id']

    @property
    def unique_id(self):
        """Return the unique string ID for the zone."""
        return '{iro}-{zone}'.format(
            iro=self._device.device_id, zone=self.zone_id)

    @property
    def number(self):
        """Return the physical connection of the zone pump."""
        return self._zone['zoneNumber']

    @property
    def name(self):
        """Return the friendly name of the zone."""
        return self._zone['name']

    @property
    def is_enabled(self):
        """Return whether the zone is allowed to run."""
        return self._zone['enabled']

    @property
    def is_on(self):
        """Return whether the zone is currently running."""
        schedule = self._device.current_schedule
        return self.zone_id == schedule.get('zoneId')

    def update(self):
        """Pull updated zone info from the Rachio API."""
        self._zone = self.rachio.zone.get(self._zone_id)[1]

        # Possibly update device
        self._device.update()

        _LOGGER.debug("Updated %s", str(self))

    def turn_on(self, **kwargs):
        """Start the zone."""
        # Stop other zones first
        self.turn_off()

        _LOGGER.info("Watering %s for %d s", self.name, self._manual_run_secs)
        self.rachio.zone.start(self.zone_id, self._manual_run_secs)

    def turn_off(self, **kwargs):
        """Stop all zones."""
        _LOGGER.info("Stopping watering of all zones")
        self.rachio.device.stopWater(self._device.device_id)
