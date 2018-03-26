"""
Support for functionality to have conversations with Home Assistant.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/conversation/
"""
import logging
import re

import voluptuous as vol

from homeassistant import core
from homeassistant.components import http
from homeassistant.components.http.data_validator import (
    RequestDataValidator)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent

from homeassistant.loader import bind_hass

_LOGGER = logging.getLogger(__name__)

ATTR_TEXT = 'text'

DEPENDENCIES = ['http']
DOMAIN = 'conversation'

REGEX_TURN_COMMAND = re.compile(r'turn (?P<name>(?: |\w)+) (?P<command>\w+)')
REGEX_TYPE = type(re.compile(''))

SERVICE_PROCESS = 'process'

SERVICE_PROCESS_SCHEMA = vol.Schema({
    vol.Required(ATTR_TEXT): cv.string,
})

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({
    vol.Optional('intents'): vol.Schema({
        cv.string: vol.All(cv.ensure_list, [cv.string])
    })
})}, extra=vol.ALLOW_EXTRA)


@core.callback
@bind_hass
def async_register(hass, intent_type, utterances):
    """Register utterances and any custom intents.

    Registrations don't require conversations to be loaded. They will become
    active once the conversation component is loaded.
    """
    intents = hass.data.get(DOMAIN)

    if intents is None:
        intents = hass.data[DOMAIN] = {}

    conf = intents.get(intent_type)

    if conf is None:
        conf = intents[intent_type] = []

    for utterance in utterances:
        if isinstance(utterance, REGEX_TYPE):
            conf.append(utterance)
        else:
            conf.append(_create_matcher(utterance))


async def async_setup(hass, config):
    """Register the process service."""
    config = config.get(DOMAIN, {})
    intents = hass.data.get(DOMAIN)

    if intents is None:
        intents = hass.data[DOMAIN] = {}

    for intent_type, utterances in config.get('intents', {}).items():
        conf = intents.get(intent_type)

        if conf is None:
            conf = intents[intent_type] = []

        conf.extend(_create_matcher(utterance) for utterance in utterances)

    async def process(service):
        """Parse text into commands."""
        text = service.data[ATTR_TEXT]
        try:
            await _process(hass, text)
        except intent.IntentHandleError as err:
            _LOGGER.error('Error processing %s: %s', text, err)

    hass.services.async_register(
        DOMAIN, SERVICE_PROCESS, process, schema=SERVICE_PROCESS_SCHEMA)

    hass.http.register_view(ConversationProcessView)

    # We strip trailing 's' from name because our state matcher will fail
    # if a letter is not there. By removing 's' we can match singular and
    # plural names.

    async_register(hass, intent.INTENT_TURN_ON, [
        'Turn [the] [a] {name}[s] on',
        'Turn on [the] [a] [an] {name}[s]',
    ])
    async_register(hass, intent.INTENT_TURN_OFF, [
        'Turn [the] [a] [an] {name}[s] off',
        'Turn off [the] [a] [an] {name}[s]',
    ])
    async_register(hass, intent.INTENT_TOGGLE, [
        'Toggle [the] [a] [an] {name}[s]',
        '[the] [a] [an] {name}[s] toggle',
    ])

    return True


def _create_matcher(utterance):
    """Create a regex that matches the utterance."""
    # Split utterance into parts that are type: NORMAL, GROUP or OPTIONAL
    # Pattern matches (GROUP|OPTIONAL): Change light to [the color] {name}
    parts = re.split(r'({\w+}|\[[\w\s]+\] *)', utterance)
    # Pattern to extract name from GROUP part. Matches {name}
    group_matcher = re.compile(r'{(\w+)}')
    # Pattern to extract text from OPTIONAL part. Matches [the color]
    optional_matcher = re.compile(r'\[([\w ]+)\] *')

    pattern = ['^']
    for part in parts:
        group_match = group_matcher.match(part)
        optional_match = optional_matcher.match(part)

        # Normal part
        if group_match is None and optional_match is None:
            pattern.append(part)
            continue

        # Group part
        if group_match is not None:
            pattern.append(
                r'(?P<{}>[\w ]+?)\s*'.format(group_match.groups()[0]))

        # Optional part
        elif optional_match is not None:
            pattern.append(r'(?:{} *)?'.format(optional_match.groups()[0]))

    pattern.append('$')
    return re.compile(''.join(pattern), re.I)


async def _process(hass, text):
    """Process a line of text."""
    intents = hass.data.get(DOMAIN, {})

    for intent_type, matchers in intents.items():
        for matcher in matchers:
            match = matcher.match(text)

            if not match:
                continue

            response = await hass.helpers.intent.async_handle(
                DOMAIN, intent_type,
                {key: {'value': value} for key, value
                 in match.groupdict().items()}, text)
            return response


class ConversationProcessView(http.HomeAssistantView):
    """View to retrieve shopping list content."""

    url = '/api/conversation/process'
    name = "api:conversation:process"

    @RequestDataValidator(vol.Schema({
        vol.Required('text'): str,
    }))
    async def post(self, request, data):
        """Send a request for processing."""
        hass = request.app['hass']

        try:
            intent_result = await _process(hass, data['text'])
        except intent.IntentHandleError as err:
            intent_result = intent.IntentResponse()
            intent_result.async_set_speech(str(err))

        if intent_result is None:
            intent_result = intent.IntentResponse()
            intent_result.async_set_speech("Sorry, I didn't understand that")

        return self.json(intent_result)
