import re

import bottle
from bottle import delete, post, HTTPResponse

try:
    from collections import OrderedDict
except ImportError:
    #2.6 compatibility
    from pretenders.compat.ordered_dict import OrderedDict

from collections import defaultdict

from pretenders.base import get_logger
from pretenders.constants import FOREVER
from pretenders.http import Preset, MatchRule, match_rule_from_dict


LOGGER = get_logger('pretenders.boss.apps.preset')
PRESETS = defaultdict(OrderedDict)


def preset_count(uid):
    """
    Check whether there are any presets.
    """
    return len(PRESETS[uid])


def select_preset(uid, request):
    """
    Select a preset to respond with.

    Look through the presets for a match. If one is found pop off a preset
    response and return it.

    :param uid: The uid to look up presets for
    :param request: A dictionary representign the mock request. The 'value' item
        is used to match against the regexes stored in presets. They are assumed
        to be in the same sequence as those of the regexes.

    Return 404 if no preset found that matches.
    """
    preset_dict = PRESETS[uid]
    
    for key, preset_list in preset_dict.items():
        print("KEY: {0}".format(key.as_dict()))
        print("PRESET_LIST: {0}".format([p.as_dict() for p in preset_list]))

    for key, preset_list in preset_dict.items():
        preset = preset_list[0]
        print("PRESET {0}".format(preset))
        rule = match_rule_from_dict(preset.rule)
        if rule.is_match(request):
            knock_off_preset(preset_dict, key)
            return preset

    raise HTTPResponse(b"No matching preset response", status=404)


def knock_off_preset(preset_dict, key):
    """Knock a count off the preset at in list ``key`` within ``preset_dict``.

    Reduces the ``times`` paramter of a preset.
    Once the ``times`` reduces to zero it is removed.
    If ``times`` is ``FOREVER`` nothing happens.

    :param preset_dict:
        A dictionary containing preset dictionaries specific for a uid.

    :param key:
        The key pointing to the list to look up and pop an item from.
    """
    preset = preset_dict[key][0]
    if preset.times == FOREVER:
        return
    elif preset.times > 0:
        preset.times -= 1

    if preset.times == 0:
        del preset_dict[key][0]
        if not preset_dict[key]:
            del preset_dict[key]


@post('/preset/<uid:int>')
def add_preset(uid):
    """
    Save the incoming request body as a preset response
    """
    preset = Preset(json_data=bottle.request.body.read())
    if preset.times != FOREVER and preset.times <= 0:
        raise HTTPResponse(("Preset has {0} times. Must be greater than "
                             "zero.".format(preset.times).encode()),
                           status=400)

    rule = match_rule_from_dict(preset.rule)

    if rule not in PRESETS[uid]:
        PRESETS[uid][rule] = []
    url_presets = PRESETS[uid][rule]
    url_presets.append(preset)


@delete('/preset/<uid:int>')
def clear_presets(uid):
    """
    Delete all recorded presets
    """
    PRESETS[uid].clear()
