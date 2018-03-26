"""
Support for Volvo On Call.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/volvooncall/
"""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD,
                                 CONF_NAME, CONF_RESOURCES)
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_point_in_utc_time
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.util.dt import utcnow

DOMAIN = 'volvooncall'

DATA_KEY = DOMAIN

REQUIREMENTS = ['volvooncall==0.4.0']

_LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=1)

CONF_UPDATE_INTERVAL = 'update_interval'
CONF_REGION = 'region'
CONF_SERVICE_URL = 'service_url'
CONF_SCANDINAVIAN_MILES = 'scandinavian_miles'

SIGNAL_VEHICLE_SEEN = '{}.vehicle_seen'.format(DOMAIN)

RESOURCES = {'position': ('device_tracker',),
             'lock': ('lock', 'Lock'),
             'heater': ('switch', 'Heater', 'mdi:radiator'),
             'odometer': ('sensor', 'Odometer', 'mdi:speedometer', 'km'),
             'fuel_amount': ('sensor', 'Fuel amount', 'mdi:gas-station', 'L'),
             'fuel_amount_level': (
                 'sensor', 'Fuel level', 'mdi:water-percent', '%'),
             'average_fuel_consumption': (
                 'sensor', 'Fuel consumption', 'mdi:gas-station', 'L/100 km'),
             'distance_to_empty': ('sensor', 'Range', 'mdi:ruler', 'km'),
             'washer_fluid_level': ('binary_sensor', 'Washer fluid'),
             'brake_fluid': ('binary_sensor', 'Brake Fluid'),
             'service_warning_status': ('binary_sensor', 'Service'),
             'bulb_failures': ('binary_sensor', 'Bulbs'),
             'doors': ('binary_sensor', 'Doors'),
             'windows': ('binary_sensor', 'Windows')}

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): (
            vol.All(cv.time_period, vol.Clamp(min=MIN_UPDATE_INTERVAL))),
        vol.Optional(CONF_NAME, default={}): vol.Schema(
            {cv.slug: cv.string}),
        vol.Optional(CONF_RESOURCES): vol.All(
            cv.ensure_list, [vol.In(RESOURCES)]),
        vol.Optional(CONF_REGION): cv.string,
        vol.Optional(CONF_SERVICE_URL): cv.string,
        vol.Optional(CONF_SCANDINAVIAN_MILES, default=False): cv.boolean,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Volvo On Call component."""
    from volvooncall import Connection
    connection = Connection(
        config[DOMAIN].get(CONF_USERNAME),
        config[DOMAIN].get(CONF_PASSWORD),
        config[DOMAIN].get(CONF_SERVICE_URL),
        config[DOMAIN].get(CONF_REGION))

    interval = config[DOMAIN].get(CONF_UPDATE_INTERVAL)

    state = hass.data[DATA_KEY] = VolvoData(config)

    def discover_vehicle(vehicle):
        """Load relevant platforms."""
        state.entities[vehicle.vin] = []
        for attr, (component, *_) in RESOURCES.items():
            if (getattr(vehicle, attr + '_supported', True) and
                    attr in config[DOMAIN].get(CONF_RESOURCES, [attr])):
                discovery.load_platform(
                    hass, component, DOMAIN, (vehicle.vin, attr), config)

    def update_vehicle(vehicle):
        """Receive updated information on vehicle."""
        state.vehicles[vehicle.vin] = vehicle
        if vehicle.vin not in state.entities:
            discover_vehicle(vehicle)

        for entity in state.entities[vehicle.vin]:
            entity.schedule_update_ha_state()

        dispatcher_send(hass, SIGNAL_VEHICLE_SEEN, vehicle)

    def update(now):
        """Update status from the online service."""
        try:
            if not connection.update():
                _LOGGER.warning("Could not query server")
                return False

            for vehicle in connection.vehicles:
                update_vehicle(vehicle)

            return True
        finally:
            track_point_in_utc_time(hass, update, utcnow() + interval)

    _LOGGER.info("Logging in to service")
    return update(utcnow())


class VolvoData:
    """Hold component state."""

    def __init__(self, config):
        """Initialize the component state."""
        self.entities = {}
        self.vehicles = {}
        self.config = config[DOMAIN]
        self.names = self.config.get(CONF_NAME)

    def vehicle_name(self, vehicle):
        """Provide a friendly name for a vehicle."""
        if (vehicle.registration_number and
                vehicle.registration_number.lower()) in self.names:
            return self.names[vehicle.registration_number.lower()]
        elif (vehicle.vin and
              vehicle.vin.lower() in self.names):
            return self.names[vehicle.vin.lower()]
        elif vehicle.registration_number:
            return vehicle.registration_number
        elif vehicle.vin:
            return vehicle.vin
        return ''


class VolvoEntity(Entity):
    """Base class for all VOC entities."""

    def __init__(self, hass, vin, attribute):
        """Initialize the entity."""
        self._hass = hass
        self._vin = vin
        self._attribute = attribute
        self._state.entities[self._vin].append(self)

    @property
    def _state(self):
        return self._hass.data[DATA_KEY]

    @property
    def vehicle(self):
        """Return vehicle."""
        return self._state.vehicles[self._vin]

    @property
    def _entity_name(self):
        return RESOURCES[self._attribute][1]

    @property
    def _vehicle_name(self):
        return self._state.vehicle_name(self.vehicle)

    @property
    def name(self):
        """Return full name of the entity."""
        return '{} {}'.format(
            self._vehicle_name,
            self._entity_name)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return dict(model='{}/{}'.format(
            self.vehicle.vehicle_type,
            self.vehicle.model_year))
