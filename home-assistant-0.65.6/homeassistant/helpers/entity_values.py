"""A class to hold entity values."""
from collections import OrderedDict
import fnmatch
import re

from homeassistant.core import split_entity_id


class EntityValues(object):
    """Class to store entity id based values."""

    def __init__(self, exact=None, domain=None, glob=None):
        """Initialize an EntityConfigDict."""
        self._cache = {}
        self._exact = exact
        self._domain = domain

        if glob is None:
            compiled = None
        else:
            compiled = OrderedDict()
            for key, value in glob.items():
                compiled[re.compile(fnmatch.translate(key))] = value

        self._glob = compiled

    def get(self, entity_id):
        """Get config for an entity id."""
        if entity_id in self._cache:
            return self._cache[entity_id]

        domain, _ = split_entity_id(entity_id)
        result = self._cache[entity_id] = {}

        if self._domain is not None and domain in self._domain:
            result.update(self._domain[domain])

        if self._glob is not None:
            for pattern, values in self._glob.items():
                if pattern.match(entity_id):
                    result.update(values)

        if self._exact is not None and entity_id in self._exact:
            result.update(self._exact[entity_id])

        return result
