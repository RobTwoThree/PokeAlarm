# Standard Library Imports
import logging
import requests
# 3rd Party Imports
# Local Imports
from ..Alarm import Alarm
from ..Utils import parse_boolean, get_static_map_url, reject_leftover_parameters, require_and_remove_key, get_time_as_str

log = logging.getLogger('Discord')
try_sending = Alarm.try_sending
replace = Alarm.replace

#####################################################  ATTENTION!  #####################################################
# You DO NOT NEED to edit this file to customize messages for services! Please see the Wiki on the correct way to
# customize services In fact, doing so will likely NOT work correctly with many features included in PokeAlarm.
#                               PLEASE ONLY EDIT IF YOU KNOW WHAT YOU ARE DOING!
#####################################################  ATTENTION!  #####################################################


class DiscordAlarm(Alarm):

    _defaults = {
        'pokemon': {
            'username': "<pkmn>",
            'content':"",
            'icon_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/<pkmn_id>.png",
            'avatar_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/<pkmn_id>.png",
            'title': "A wild <pkmn> has appeared!",
            'url': "<gmaps>",
            'body': "Available until <24h_time> (<time_left>).",
            'color': ""
        },
        'pokestop': {
            'username': "Pokestop",
            'content': "",
            'icon_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/pokestop.png",
            'avatar_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/pokestop.png",
            'title': "Someone has placed a lure on a Pokestop!",
            'url': "<gmaps>",
            'body': "Lure will expire at <24h_time> (<time_left>).",
            'color': ""
        },
        'gym': {
            'username': "<name>",
            'content': "",
            'icon_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/gym_<team_id>.png",
            'avatar_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/gym_<team_id>.png",
            'title': "<name> gym has fallen!",
            'url': "<gmaps>",
            'body': "It is now controlled by <new_team>.\Previously controlled by: <old_team>",
            'color': ""
        },
        'raid': {
            'username': "Raid",
            'content': "",
            'icon_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/gym_<team_id>.png",
            'avatar_url': "https://raw.githubusercontent.com/fosJoddie/PokeAlarm/raids/icons/egg_<raid_level>.png",
            'title': "Level <raid_level> Raid is available against <pkmn>!",
            'url': "<gmaps>",
            'body': "The raid is available until <24h_time> (<time_left>).",
            'color': "<gym_team>"
        },
        'egg': {
            'username': "Egg",
            'content': "",
            'icon_url': "https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/gym_<team_id>.png",
            'avatar_url': "https://raw.githubusercontent.com/fosJoddie/PokeAlarm/raids/icons/egg_<raid_level>.png",
            'title': "Raid is incoming!",
            'url': "<gmaps>",
            'body': "A level <raid_level> raid will hatch <begin_24h_time> (<begin_time_left>).",
            'color': "<gym_team>"
        }
    }

    # Gather settings and create alarm
    def __init__(self, settings, max_attempts, static_map_key):
        # Required Parameters
        self.__webhook_url = require_and_remove_key('webhook_url', settings, "'Discord' type alarms.")
        self.__max_attempts = max_attempts

        # Optional Alarm Parameters
        self.__startup_message = parse_boolean(settings.pop('startup_message', "True"))
        self.__disable_embed = parse_boolean(settings.pop('disable_embed', "False"))
        self.__avatar_url = settings.pop('avatar_url', "")
        self.__map = settings.pop('map', {})  # default for the rest of the alerts
        self.__static_map_key = static_map_key

        # Set Alert Parameters
        self.__pokemon = self.create_alert_settings(settings.pop('pokemon', {}), self._defaults['pokemon'])
        self.__pokestop = self.create_alert_settings(settings.pop('pokestop', {}), self._defaults['pokestop'])
        self.__gym = self.create_alert_settings(settings.pop('gym', {}), self._defaults['gym'])
        self.__raid = self.create_alert_settings(settings.pop('raid', {}), self._defaults['raid'])
        self.__egg = self.create_alert_settings(settings.pop('egg', {}), self._defaults['egg'])

        # Warn user about leftover parameters
        reject_leftover_parameters(settings, "'Alarm level in Discord alarm.")

        log.info("Discord Alarm has been created!")

    # (Re)connect with Discord
    def connect(self):
        pass

    # Send a message letting the channel know that this alarm has started
    def startup_message(self):
        if self.__startup_message:
            args = {
                'url': self.__webhook_url,
                'payload': {
                    'username': 'PokeAlarm',
                    'content': 'PokeAlarm activated!'
                }
            }
            try_sending(log, self.connect, "Discord", self.send_webhook, args, self.__max_attempts)
            log.info("Startup message sent!")

    # Set the appropriate settings for each alert
    def create_alert_settings(self, settings, default):
        alert = {
            'webhook_url': settings.pop('webhook_url', self.__webhook_url),
            'username': settings.pop('username', default['username']),
            'avatar_url': settings.pop('avatar_url', default['avatar_url']),
            'disable_embed': parse_boolean(settings.pop('disable_embed', self.__disable_embed)),
            'content': settings.pop('content', default['content']),
            'icon_url': settings.pop('icon_url', default['icon_url']),
            'title': settings.pop('title', default['title']),
            'url': settings.pop('url', default['url']),
            'body': settings.pop('body', default['body']),
            'color': settings.pop('color', default['color']),
            'map': get_static_map_url(settings.pop('map', self.__map), self.__static_map_key)
        }

        reject_leftover_parameters(settings, "'Alert level in Discord alarm.")
        return alert

    # Send Alert to Discord
    def send_alert(self, alert, info):
        log.debug("Attempting to send notification to Discord.")
        color_code = replace(alert['color'], info)
        username_text = replace(alert['username'], info)[:32]
        color_to_display = 0x000000
        log.debug("Color code provided: {}".format(color_code))
        gym_name = info['gym_name']
        raid_begin = get_time_as_str(info['raid_begin'], None)
        raid_end = get_time_as_str(info['expire_time'], None)
        cp = info['cp']

        if gym_name == "":
            gym_name_to_display = "*Gym name unknown.*"
        else:
            gym_name_to_display = gym_name + " Gym"
            if gym_name in ("GET YOUR LEVEL BADGE", "GET MORE FREE ITEMS"):
                gym_name_to_display = "Sprint Store Gym"


        if gym_name in ("Starbucks", "GET YOUR LEVEL BADGE", "GET MORE FREE ITEMS"):
            if cp == 0:
                username_text = "SPONSORED L-" + str(info['raid_level']) + " EGG: " + str(raid_end[1])
            else:
                username_text = "SPONSORED L-" + str(info['raid_level']) + " RAID: " + str(info['pkmn'])

        if cp == 0:
            raid_details = "Egg Level: " + str(info['raid_level']) + "\nLaid at: " + str(raid_begin[1]) + "\nHatches at: " + str(raid_end[1]) + "\nCoords: (" + str(info['lat']) + ", " + str(info['lng']) + ")"
        else:
            raid_details = "Raid Level: " + str(info['raid_level']) + "\nBoss: " + str(info['pkmn']) + "\nCP: " + str(info['cp']) + "\nQuick Move: " + str(info['quick_move']) + "\nCharge Move: " + str(info['charge_move']) + "\n\nStarts at: " + str(raid_begin[1]) + "\nEnds at: " + str(raid_end[1])  + "\nCoords: (" + str(info['lat']) + ", " + str(info['lng']) + ")"

        log.debug("Pull data: {}".format(gym_name_to_display))
        
        if color_code == "Mystic":
            color_to_display = 0x2447ff
        if color_code == "Valor":
            color_to_display = 0xff2050
        if color_code == "Instinct":
            color_to_display = 0xffe20e
        
        payload = {
            'username': username_text,  # Username must be 32 characters or less
            #'content': replace(alert['content'], info),
            'avatar_url':  replace(alert['avatar_url'], info),
        }
        if alert['disable_embed'] is False:
            payload['embeds'] = [{
                'title': replace(alert['title'], info),
                'url': replace(alert['url'], info),
                #'description': gym_name_to_display, # Removed for now. Save for later use
                'thumbnail': {'url': replace(alert['icon_url'], info)},
                'color': color_to_display,
                'fields': [
                    {
                        'name': "Gym Name:",
                        'value': gym_name_to_display
                    },
                    {
                        'name': "Occupied by:",
                        'value': "Team " + info['gym_team']
                    },
                    {
                        'name': "Raid Details:",
                        'value': raid_details
                    }
                ]
            }]
            if alert['map'] is not None:
                payload['embeds'][0]['image'] = {'url': replace(alert['map'], {'lat': info['lat'], 'lng': info['lng']})}
        args = {
            'url': alert['webhook_url'],
            'payload': payload
        }
        try_sending(log, self.connect, "Discord", self.send_webhook, args, self.__max_attempts)

    # Trigger an alert based on Pokemon info
    def pokemon_alert(self, pokemon_info):
        log.debug("Pokemon notification triggered.")
        self.send_alert(self.__pokemon, pokemon_info)

    # Trigger an alert based on Pokestop info
    def pokestop_alert(self, pokestop_info):
        log.debug("Pokestop notification triggered.")
        self.send_alert(self.__pokestop, pokestop_info)

    # Trigger an alert based on Pokestop info
    def gym_alert(self, gym_info):
        log.debug("Gym notification triggered.")
        self.send_alert(self.__gym, gym_info)

    # Trigger an alert when a raid egg has spawned (UPCOMING raid event)
    def raid_egg_alert(self, raid_info):
        self.send_alert(self.__egg, raid_info)

    def raid_alert(self, raid_info):
        self.send_alert(self.__raid, raid_info)

    # Send a payload to the webhook url
    def send_webhook(self, url, payload):
        log.debug(payload)
        resp = requests.post(url, json=payload, timeout=(None, 5))
        if resp.ok is True:
            log.debug("Notification successful (returned {})".format(resp.status_code))
        else:
            log.debug("Discord response was {}".format(resp.content))
            raise requests.exceptions.RequestException(
                "Response received {}, webhook not accepted.".format(resp.status_code))
