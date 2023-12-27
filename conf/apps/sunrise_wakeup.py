

from datetime import datetime, timedelta
from typing import List
from typing import Any
from dataclasses import dataclass

from appdaemon.plugins.hass.hassapi import Hass

@dataclass
class EventConfig:
    """Event Config Class - Event Data is passed from the automation framework to the app via event trigger"""

    max_sunrise_wakeup_runtime: int
    lights_max_brightness: int
    media_players_max_volume: float
    lights_max_brightness_after: int
    media_players_max_volume_after: int

    @staticmethod
    def from_dict(obj: Any) -> "EventConfig":
        _max_sunrise_wakeup_runtime = int(obj.get("max_sunrise_wakeup_runtime"))
        _lights_max_brightness = int(obj.get("lights_max_brightness"))
        _media_players_max_volume = float(obj.get("media_players_max_volume"))
        _lights_max_brightness_after = int(obj.get("lights_max_brightness_after"))
        _media_players_max_volume_after = int(obj.get("media_players_max_volume_after"))
        return EventConfig(
            _max_sunrise_wakeup_runtime,
            _lights_max_brightness,
            _media_players_max_volume,
            _lights_max_brightness_after,
            _media_players_max_volume_after,
        )

@dataclass
class Context:
    """Context Class - Event Data is passed from the automation framework to the app via event trigger"""

    id: str
    parent_id: str
    user_id: str

    @staticmethod
    def from_dict(obj: Any) -> "Context":
        _id = str(obj.get("id"))
        _parent_id = str(obj.get("parent_id"))
        _user_id = str(obj.get("user_id"))
        return Context(_id, _parent_id, _user_id)

@dataclass
class Metadata:
    """Metadata Class - Event Data is passed from the automation framework to the app via event trigger"""

    origin: str
    time_fired: str
    context: Context

    @staticmethod
    def from_dict(obj: Any) -> "Metadata":
        _origin = str(obj.get("origin"))
        _time_fired = str(obj.get("time_fired"))
        _context = Context.from_dict(obj.get("context"))
        return Metadata(_origin, _time_fired, _context)

@dataclass
class StartWakeupEvent:
    """Start Wakeup Event Class - Event Data is passed from the automation framework to the app via event trigger"""

    light_ids: List[str]
    media_players: List[str]
    event_config: EventConfig
    metadata: Metadata

    @staticmethod
    def from_dict(obj: Any) -> "StartWakeupEvent":
        _light_ids = [str(x) for x in obj.get("light_ids")]
        _media_players = [str(x) for x in obj.get("media_players")]
        _event_config = EventConfig.from_dict(obj.get("config"))
        _metadata = Metadata.from_dict(obj.get("metadata"))
        return StartWakeupEvent(_light_ids, _media_players, _event_config, _metadata)

class WakeupConfig:
    """Wake Up Config Class"""

    def __init__(self, event_config: EventConfig) -> None:
        """Initialize the Wake Up Config"""
        self.routine_start_time = datetime.now()
        self.routine_automatic_end_time = self.routine_start_time  + timedelta(seconds=event_config.max_sunrise_wakeup_runtime * 60)

        self.lights_rgb_helper = 0
        self.lights_rgb_helper_max = 100
        self.lights_rgb_color = [240, self.lights_rgb_helper, 40]

        self.lights_brightness_initial = 1
        self.lights_rgb_color_initial = [240, self.lights_rgb_helper, 40]
        self.media_players_volume_initial = 0.02

        self.max_sunrise_wakeup_runtime_in_seconds = event_config.max_sunrise_wakeup_runtime * 60

        self.lights_max_brightness = event_config.lights_max_brightness
        self.lights_max_brightness_after_in_seconds = event_config.lights_max_brightness_after * 60

        self.media_player_max_volume = event_config.media_players_max_volume
        self.media_player_max_volume_after_in_seconds = event_config.media_players_max_volume_after * 60

        self.dynamic_lights_brightness_step_size = self.lights_max_brightness / self.lights_max_brightness_after_in_seconds
        self.dynamic_lights_rgb_step_size = self.lights_rgb_helper_max / (self.lights_max_brightness_after_in_seconds * 0.5)

        self.dynamic_media_player_volume_step_size = self.media_player_max_volume / self.media_player_max_volume_after_in_seconds

        self.media_playlist = "spotify://88b68d2d78123f3a3850a0703d6729a2/spotify:playlist:43Q9LvUErcQvo4YzG2wd5k"

class SunriseWakeupApp(Hass):
    """Sunrise Wakeup App for AppDaemon"""

    start_wakeup_event: StartWakeupEvent = None

    abort_sunrise_wakeup: bool = False
    sunrise_wakeup_running: bool = False

    lights_brightness_current: int = 0
    lights_rgb_helper_current: int = 0
    lights_rgb_color_current = []
    media_players_volume_current: float = 0.00

    ready_devices = []
    devices_ready_to_start_handles = []
    state_change_handles = []

    def initialize(self):
        """Initialize the app"""
        self.listen_event(self.start_event_sunrise_wakeup, event="sunrise_wakeup_start_trigger")
        self.listen_event(self.stop_event_sunrise_wakeup, event="sunrise_wakeup_stop_trigger")


    def set_initial_devices_state(self, start_wakeup_event: StartWakeupEvent):
        """Set initial devices state"""

        if self.wakeup_config.lights_brightness_initial < 1:
            self.log("WakeupApp :: ROUTINE :: Initial brightness is lower than 1. Setting it to 1", level="WARNING")
            self.wakeup_config.lights_brightness_initial = 1

        for light_id in start_wakeup_event.light_ids:
            self.call_service(
                "light/turn_on",
                entity_id=light_id,
                brightness=self.wakeup_config.lights_brightness_initial,
                rgb_color=self.wakeup_config.lights_rgb_color_initial,
                transition=0,
            )
        for media_player in start_wakeup_event.media_players:
            self.call_service(
                "media_player/volume_set",
                entity_id=media_player,
                volume_level=self.wakeup_config.media_players_volume_initial,
            )

        self.log("WakeupApp :: ROUTINE :: Initial State set", level="INFO")

    def devices_ready_to_start(self, entity, attribute, old, new, kwargs):
        """Check if all devices are ready to start"""

        self.log(f"WakeupApp :: ROUTINE :: Device: {entity} with new state: {new}", level="INFO")
        if (new == "on" or new == "playing") and entity not in self.ready_devices:
            self.ready_devices.append(entity)

        if len(self.ready_devices) == len(self.start_wakeup_event.light_ids + self.start_wakeup_event.media_players):
            self.log("WakeupApp :: ROUTINE :: All devices ready to start", level="INFO")
            self.ready_devices = []
            for handle in self.devices_ready_to_start_handles:
                self.cancel_listen_state(handle)
            self.devices_ready_to_start_handles = []

            for light_id in self.start_wakeup_event.light_ids:
                self.state_change_handles.append(self.listen_state(self.device_state_changed, light_id))
            for media_player in self.start_wakeup_event.media_players:
                self.state_change_handles.append(self.listen_state(self.device_state_changed, media_player))

            self.log("WakeupApp :: ROUTINE :: Start increase volume and brightness", level="INFO")
            self.run_in(self.wakeup_routine, 4)

    def start_event_sunrise_wakeup(self, event_name, data, kwargs):
        """Sunrise Wake Up start event handler"""

        self.log("WakeupApp :: EVENT :: Start", level="INFO")

        if self.sunrise_wakeup_running:
            self.log("WakeupApp :: EVENT :: Already running", level="INFO")
            return
        self.sunrise_wakeup_running = True
        self.abort_sunrise_wakeup = False
        self.start_wakeup_event = StartWakeupEvent.from_dict(data)
        self.wakeup_config = WakeupConfig(event_config=self.start_wakeup_event.event_config)

        if(self.start_wakeup_event.light_ids is None or self.start_wakeup_event.media_players is None):
            self.log("WakeupApp :: EVENT :: No Light or Media Player defined", level="INFO")
            return

        self.log(f"WakeupApp :: EVENT :: End Time: {self.wakeup_config.routine_automatic_end_time}", level="INFO")

        self.lights_brightness_current = self.wakeup_config.lights_brightness_initial
        self.lights_rgb_helper_current = self.wakeup_config.lights_rgb_helper
        self.lights_rgb_color_current = self.wakeup_config.lights_rgb_color
        self.media_players_volume_current = self.wakeup_config.media_players_volume_initial

        # log the initial state, and config values including dynamic values
        self.log(f"WakeupApp :: SETTINGS :: Max Runtime: {self.wakeup_config.max_sunrise_wakeup_runtime_in_seconds} seconds | Lights Max Brightness: {self.wakeup_config.lights_max_brightness:.2f} | Media Player Max Volume: {self.wakeup_config.media_player_max_volume:.2f} | Dynamic Lights Brightness Step Size: {self.wakeup_config.dynamic_lights_brightness_step_size:.2f} | Dynamic Lights RGB Step Size: {self.wakeup_config.dynamic_lights_rgb_step_size:.2f} | Dynamic Media Player Volume Step Size: {self.wakeup_config.dynamic_media_player_volume_step_size:.2f}", level="INFO")

        # Check current state of the devices
        for light_id in self.start_wakeup_event.light_ids:
            light_state = self.get_state(light_id)
            if light_state == "on":
                self.log(f"WakeupApp :: EVENT :: Light: {light_id} is already on. Will not start wakeup routine", level="INFO")
                self.sunrise_wakeup_running = False
                self.abort_sunrise_wakeup = True
                return
            
        for media_player in self.start_wakeup_event.media_players:
            media_player_state = self.get_state(media_player)
            if media_player_state == "playing":
                self.log(f"WakeupApp :: EVENT :: Media Player: {media_player} is already playing. Will not start wakeup routine", level="INFO")
                self.sunrise_wakeup_running = False
                self.abort_sunrise_wakeup = True
                return

        # We only want to start the routine if all devices are ready (lights = on and media player = playing)
        for light_id in self.start_wakeup_event.light_ids:
            self.devices_ready_to_start_handles.append(self.listen_state(self.devices_ready_to_start, light_id))
        for media_player in self.start_wakeup_event.media_players:
            self.devices_ready_to_start_handles.append(self.listen_state(self.devices_ready_to_start, media_player))

        self.set_initial_devices_state(self.start_wakeup_event)

        self.call_service(
            "media_player/play_media",
            entity_id=self.start_wakeup_event.media_players[0],
            media_content_id=self.wakeup_config.media_playlist,
            media_content_type="playlist",
        )

        self.call_service(
            "media_player/media_play",
            entity_id=self.start_wakeup_event.media_players[0],
        )
    
    def turn_off_devices(self):
        """Turn off devices"""

        for light_id in self.start_wakeup_event.light_ids:
            self.call_service("light/turn_off", entity_id=light_id)
        for media_player in self.start_wakeup_event.media_players:
            self.call_service("media_player/media_pause", entity_id=media_player)
        
    def stop_sunrise_routine(self):
        """Stop the sunrise routine"""

        self.log("WakeupApp :: ROUTINE :: Stopping", level="INFO")
        for handle in self.state_change_handles:
            self.cancel_listen_state(handle)
        self.state_change_handles = []

        self.sunrise_wakeup_running = False
        self.abort_sunrise_wakeup = True

        self.turn_off_devices()

        self.log("WakeupApp :: ROUTINE :: Stopped", level="INFO")

    def stop_event_sunrise_wakeup(self, event_name, data, kwargs):
        """Sunrise Wake Up stop event handler"""

        self.log("WakeupApp :: EVENT :: Stop", level="INFO")
        self.stop_sunrise_routine()

    def device_state_changed(self, entity, attribute, old, new, kwargs):        
        """Device state changed event handler"""

        if not self.abort_sunrise_wakeup:
            self.log(f"WakeupApp :: EVENT :: Device: {entity} with new state: {new}", level="INFO")
            if new == "off" or new == "paused":
                self.log(f"WakeupApp :: EVENT :: Device: {entity} with new used state: {new}", level="INFO")
                self.stop_sunrise_routine()

    def max_wakeup_time_reached(self) -> bool:
        """Check if max runtime reached"""

        if datetime.now() > self.wakeup_config.routine_automatic_end_time:
            self.log("WakeupApp :: ROUTINE :: Max Runtime reached", level="INFO")
            return True
        return False

    def wakeup_routine(self, kwargs):
        """Wakeup routine"""
        
        if not self.max_wakeup_time_reached() and not self.abort_sunrise_wakeup:
            
            self.lights_brightness_current += self.wakeup_config.dynamic_lights_brightness_step_size
            if self.lights_brightness_current >= self.wakeup_config.lights_max_brightness:
                self.lights_brightness_current = self.wakeup_config.lights_max_brightness
                
            self.lights_rgb_helper_current += self.wakeup_config.dynamic_lights_rgb_step_size
            if self.lights_rgb_helper_current >= self.wakeup_config.lights_rgb_helper_max:
                self.lights_rgb_helper_current = self.wakeup_config.lights_rgb_helper_max
            
            self.lights_rgb_color_current = [240, self.lights_rgb_helper_current, 40]

            self.media_players_volume_current += self.wakeup_config.dynamic_media_player_volume_step_size
            if self.media_players_volume_current >= self.wakeup_config.media_player_max_volume:
                self.media_players_volume_current = self.wakeup_config.media_player_max_volume


            
            for light_id in self.start_wakeup_event.light_ids:
                self.call_service(
                    "light/turn_on",
                    entity_id=light_id,
                    brightness=self.lights_brightness_current,
                    rgb_color=self.lights_rgb_color_current,
                    transition=1,
                )

            for media_player in self.start_wakeup_event.media_players:
                self.call_service(
                    "media_player/volume_set", entity_id=media_player, volume_level=self.media_players_volume_current
                )


            # runtime_since_start = datetime.now() - self.wakeup_config.routine_start_time
            # media_player_volume_current_percent = self.media_players_volume_current / self.wakeup_config.media_player_max_volume * 100
            # rgb_helper_current_percent = self.lights_rgb_helper_current / self.wakeup_config.lights_rgb_helper_max * 100
            # lights_brightness_current_percent = self.lights_brightness_current / self.wakeup_config.lights_max_brightness * 100
            # self.log(f"WakeupApp :: ROUTINE :: Runtime: {runtime_since_start.seconds} seconds | RGB Helper: {rgb_helper_current_percent:.2f}% Brightness: {lights_brightness_current_percent:.2f}% | Volume: {media_player_volume_current_percent:.2f}%", level="INFO")
            self.run_in(self.wakeup_routine, 1)
        else:
            self.log("WakeupApp :: ROUTINE :: Wake up routine was ended", level="INFO")









