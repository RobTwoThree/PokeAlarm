# Standard Library Imports Test
from datetime import datetime
import logging
import traceback
# 3rd Party Imports
# Local Imports
from Utils import get_gmaps_link, get_move_damage, get_move_dps, get_move_duration,\
    get_move_energy, get_pokemon_gender, get_pokemon_size, get_applemaps_link

log = logging.getLogger('WebhookStructs')


################################################## Webhook Standards  ##################################################


# RocketMap Standards
class RocketMap:
    def __init__(self):
        raise NotImplementedError("This is a static class not meant to be initiated")

    @staticmethod
    def make_object(data):
        try:
            kind = data.get('type')
            if kind == 'pokemon':
                return RocketMap.pokemon(data.get('message'))
            elif kind == 'pokestop':
                return RocketMap.pokestop(data.get('message'))
            elif kind == 'gym' or kind == 'gym_details':
                return RocketMap.gym(data.get('message'))
            elif kind == 'raid':
                return RocketMap.raid(data.get('message'))
            elif kind in ['captcha', 'scheduler']:  # Unsupported Webhooks
                log.debug("{} webhook received. This webhooks is not yet supported at this time.".format({kind}))
            else:
                log.error("Invalid type specified ({}). Are you using the correct map type?".format(kind))
        except Exception as e:
            log.error("Encountered error while processing webhook ({}: {})".format(type(e).__name__, e))
            log.debug("Stack trace: \n {}".format(traceback.format_exc()))
        return None

    @staticmethod
    def pokemon(data):
        log.debug("Converting to pokemon: \n {}".format(data))
        # Get some stuff ahead of time (cause we are lazy)
        quick_id = check_for_none(int, data.get('move_1'), '?')
        charge_id = check_for_none(int, data.get('move_2'), '?')
        lat, lng = data['latitude'], data['longitude']
        # Generate all the non-manager specifi
        pkmn = {
            'type': "pokemon",
            'id': data['encounter_id'],
            'pkmn_id': int(data['pokemon_id']),
            'disappear_time': datetime.utcfromtimestamp(data['disappear_time']),
            'lat': float(data['latitude']),
            'lng': float(data['longitude']),
            'cp': check_for_none(int, data.get('cp'), '?'),
            'level': check_for_none(int, data.get('pokemon_level'), '?'),
            'iv': '?',
            'atk': check_for_none(int, data.get('individual_attack'), '?'),
            'def': check_for_none(int, data.get('individual_defense'), '?'),
            'sta': check_for_none(int, data.get('individual_stamina'), '?'),
            'quick_id': quick_id,
            'quick_damage': get_move_damage(quick_id),
            'quick_dps': get_move_dps(quick_id),
            'quick_duration': get_move_duration(quick_id),
            'quick_energy': get_move_energy(quick_id),
            'charge_id': charge_id,
            'charge_damage': get_move_damage(charge_id),
            'charge_dps': get_move_dps(charge_id),
            'charge_duration': get_move_duration(charge_id),
            'charge_energy': get_move_energy(charge_id),
            'height': check_for_none(float, data.get('height'), 'unkn'),
            'weight': check_for_none(float, data.get('weight'), 'unkn'),
            'gender': get_pokemon_gender(check_for_none(int, data.get('gender'), '?')),
            'form_id': check_for_none(int, data.get('form'), '?'),
            'size': 'unknown',
            'tiny_rat': '',
            'big_karp': '',
            'gmaps': get_gmaps_link(lat, lng),
            'applemaps': get_applemaps_link(lat, lng)
        }
        if pkmn['atk'] != '?' or pkmn['def'] != '?' or pkmn['sta'] != '?':
            pkmn['iv'] = float(((pkmn['atk'] + pkmn['def'] + pkmn['sta']) * 100) / float(45))
        else:
            pkmn['atk'], pkmn['def'], pkmn['sta'] = '?', '?', '?'

        if pkmn['height'] != 'unkn' or pkmn['weight'] != 'unkn':
            pkmn['size'] = get_pokemon_size(pkmn['pkmn_id'], pkmn['height'], pkmn['weight'])
            pkmn['height'] = "{:.2f}".format(pkmn['height'])
            pkmn['weight'] = "{:.2f}".format(pkmn['weight'])

        if pkmn['pkmn_id'] == 19 and pkmn['size'] == 'tiny':
            pkmn['tiny_rat'] = 'tiny'

        if pkmn['pkmn_id'] == 129 and pkmn['size'] == 'big':
            pkmn['big_karp'] = 'big'

        return pkmn

    @staticmethod
    def pokestop(data):
        log.debug("Converting to pokestop: \n {}".format(data))
        if data.get('lure_expiration') is None:
            log.debug("Un-lured pokestop... ignoring.")
            return None
        stop = {
            'type': "pokestop",
            'id': data['pokestop_id'],
            'expire_time':  datetime.utcfromtimestamp(data['lure_expiration']),
            'lat': float(data['latitude']),
            'lng': float(data['longitude'])
        }
        stop['gmaps'] = get_gmaps_link(stop['lat'], stop['lng'])
        stop['applemaps'] = get_applemaps_link(stop['lat'], stop['lng'])
        return stop

    @staticmethod
    def raid(data):
        log.debug("Converting to raid: \n {}".format(data))

        quick_id = check_for_none(int, data.get('boss_move_1'), '?')
        charge_id = check_for_none(int, data.get('boss_move_2'), '?')

        raid_end = None
        raid_begin = None

        if 'raid_begin' in data:
            raid_begin = datetime.utcfromtimestamp(data['raid_begin'] / 1000)
        elif 'battle' in data:
            raid_begin = datetime.utcfromtimestamp(data['battle'])
        elif 'start' in data:
            raid_begin = datetime.utcfromtimestamp(data['start'])

        if 'raid_end' in data:  # monocle
            raid_end = datetime.utcfromtimestamp(data['raid_end'] / 1000)
        elif 'end' in data:  # rocketmap
            raid_end = datetime.utcfromtimestamp(data['end'])

        if 'fort_id' in data:  # monocle sends a unique raid seed
            raid_seed = data.get('fort_id')
        else:
            raid_seed = data.get('gym_id')  # RM sends the gym id

        raid = {
            'type': 'raid',
            'id': data.get('fort_id',  data.get('fort_id')),
            'boss_pkmn_id': check_for_none(int, data.get('boss_pokemon_id'), 0),
            'cp': check_for_none(int, data.get('boss_cp'), '?'),
            'quick_id': quick_id,
            'quick_damage': get_move_damage(quick_id),
            'quick_dps': get_move_dps(quick_id),
            'quick_duration': get_move_duration(quick_id),
            'quick_energy': get_move_energy(quick_id),
            'charge_id': charge_id,
            'charge_damage': get_move_damage(charge_id),
            'charge_dps': get_move_dps(charge_id),
            'charge_duration': get_move_duration(charge_id),
            'charge_energy': get_move_energy(charge_id),
            'raid_level': check_for_none(int, data.get('raid_level'), 0),
            'expire_time': raid_end,
            'raid_begin': raid_begin,
            'lat': float(data['raid_lat']),
            'lng': float(data['raid_lon']),
            'gym_name': data.get('raid_gym_name')
        }
        
        raid['gmaps'] = get_gmaps_link(raid['lat'], raid['lng'])
        raid['applemaps'] = get_applemaps_link(raid['lat'], raid['lng'])

        return raid

    @staticmethod
    def gym(data):
        log.debug("Converting to gym: \n {}".format(data))
        
        gym = {
            'type': "gym",
            'id': data.get('fort_id',  data.get('fort_id')),
            'fort_id': 'id',
            'team_id': data.get('team'),
            'name': data.get('gym_name'),
            'slots': data.get('slots_available'),
            'lat': float(data['gym_lat']),
            'lng': float(data['gym_lon'])
        }
        gym['gmaps'] = get_gmaps_link(gym['lat'], gym['lng'])
        gym['applemaps'] = get_applemaps_link(gym['lat'], gym['lng'])
        return gym


# Ensure that the value isn't None but replacing with a default
def check_for_none(type_, val, default):
    return type_(val) if val is not None else default

########################################################################################################################
