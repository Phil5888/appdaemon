from appdaemon.plugins.mqtt.mqttapi import Mqtt
from typing import List
from typing import Any
from dataclasses import dataclass
import json
from model.influx_write_event import InfluxWriteEvent


@dataclass
class HomeInfo:
    home_name: str
    home_img: str
    charging_power: str
    power_unit: str

    @staticmethod
    def from_dict(obj: Any) -> "HomeInfo":
        _home_name = str(obj.get("home_name"))
        _home_img = str(obj.get("home_img"))
        _charging_power = str(obj.get("charging_power"))
        _power_unit = str(obj.get("power_unit"))
        return HomeInfo(_home_name, _home_img, _charging_power, _power_unit)


@dataclass
class PpsInfo:
    pps_list: List[object]
    total_charging_power: str
    power_unit: str
    total_battery_power: str
    updated_time: str
    pps_status: int

    @staticmethod
    def from_dict(obj: Any) -> "PpsInfo":
        _pps_list = [x for x in obj.get("pps_list")]
        _total_charging_power = str(obj.get("total_charging_power"))
        _power_unit = str(obj.get("power_unit"))
        _total_battery_power = str(obj.get("total_battery_power"))
        _updated_time = str(obj.get("updated_time"))
        _pps_status = int(obj.get("pps_status"))
        return PpsInfo(_pps_list, _total_charging_power, _power_unit, _total_battery_power, _updated_time, _pps_status)


@dataclass
class SolarbankList:
    device_pn: str
    device_sn: str
    device_name: str
    device_img: str
    battery_power: str
    bind_site_status: str
    charging_power: str
    power_unit: str
    charging_status: str
    status: str
    wireless_type: str
    main_version: str
    photovoltaic_power: str
    output_power: str
    create_time: int

    @staticmethod
    def from_dict(obj: Any) -> "SolarbankList":
        _device_pn = str(obj.get("device_pn"))
        _device_sn = str(obj.get("device_sn"))
        _device_name = str(obj.get("device_name"))
        _device_img = str(obj.get("device_img"))
        _battery_power = str(obj.get("battery_power"))
        _bind_site_status = str(obj.get("bind_site_status"))
        _charging_power = str(obj.get("charging_power"))
        _power_unit = str(obj.get("power_unit"))
        _charging_status = str(obj.get("charging_status"))
        _status = str(obj.get("status"))
        _wireless_type = str(obj.get("wireless_type"))
        _main_version = str(obj.get("main_version"))
        _photovoltaic_power = str(obj.get("photovoltaic_power"))
        _output_power = str(obj.get("output_power"))
        _create_time = int(obj.get("create_time"))
        return SolarbankList(_device_pn, _device_sn, _device_name, _device_img, _battery_power, _bind_site_status, _charging_power, _power_unit, _charging_status, _status, _wireless_type, _main_version, _photovoltaic_power, _output_power, _create_time)


@dataclass
class SolarbankInfo:
    solarbank_list: List[SolarbankList]
    total_charging_power: str
    power_unit: str
    charging_status: str
    total_battery_power: str
    updated_time: str
    total_photovoltaic_power: str
    total_output_power: str

    @staticmethod
    def from_dict(obj: Any) -> "SolarbankInfo":
        _solarbank_list = [SolarbankList.from_dict(y) for y in obj.get("solarbank_list")]
        _total_charging_power = str(obj.get("total_charging_power"))
        _power_unit = str(obj.get("power_unit"))
        _charging_status = str(obj.get("charging_status"))
        _total_battery_power = str(obj.get("total_battery_power"))
        _updated_time = str(obj.get("updated_time"))
        _total_photovoltaic_power = str(obj.get("total_photovoltaic_power"))
        _total_output_power = str(obj.get("total_output_power"))
        return SolarbankInfo(_solarbank_list, _total_charging_power, _power_unit, _charging_status, _total_battery_power, _updated_time, _total_photovoltaic_power, _total_output_power)


@dataclass
class Statistic:
    type: str
    total: str
    unit: str

    @staticmethod
    def from_dict(obj: Any) -> "Statistic":
        _type = str(obj.get("type"))
        _total = str(obj.get("total"))
        _unit = str(obj.get("unit"))
        return Statistic(_type, _total, _unit)


@dataclass
class SolixInfo:
    home_info: HomeInfo
    solar_list: List[object]
    pps_info: PpsInfo
    statistics: List[Statistic]
    topology_type: str
    solarbank_info: SolarbankInfo
    retain_load: str
    updated_time: str
    power_site_type: int
    site_id: str

    @staticmethod
    def from_dict(obj: Any) -> "SolixInfo":
        _home_info = HomeInfo.from_dict(obj.get("home_info"))
        _solar_list = [x for x in obj.get("solar_list")]
        _pps_info = PpsInfo.from_dict(obj.get("pps_info"))
        _statistics = [Statistic.from_dict(y) for y in obj.get("statistics")]
        _topology_type = str(obj.get("topology_type"))
        _solarbank_info = SolarbankInfo.from_dict(obj.get("solarbank_info"))
        _retain_load = str(obj.get("retain_load"))
        _updated_time = str(obj.get("updated_time"))
        _power_site_type = int(obj.get("power_site_type"))
        _site_id = str(obj.get("site_id"))
        return SolixInfo(_home_info, _solar_list, _pps_info, _statistics, _topology_type, _solarbank_info, _retain_load, _updated_time, _power_site_type, _site_id)


class SolixClientApp(Mqtt):
    def initialize(self):
        self.set_namespace("mqtt")
        self.mqtt_subscribe("solix/site/PhilsHome/scenInfo")
        self.listen_event(self.mqtt_message_received_event)

    def mqtt_message_received_event(self, event_name, data, kwargs):
        try:
            # check if data is a mqtt message
            if not data.get("topic"):
                return
            if len(data) == 0:
                self.log("SolixClientApp :: MQTT message :: Received with no data", level="WARNING")
                return

            if data.get("topic") != "solix/site/PhilsHome/scenInfo":
                return
            self.log(f"SolixClientApp :: MQTT message :: Topic {data['topic']} received", level="INFO")
            solix_info = SolixInfo.from_dict(json.loads(data["payload"]))

            influx_data = []

            for solarbank in solix_info.solarbank_info.solarbank_list:
                influx_data.append({"measurement": solarbank.device_name, "tags": {}, "fields": {"battery_power": solarbank.battery_power, "charging_power": solarbank.charging_power, "photovoltaic_power": solarbank.photovoltaic_power, "output_power": solarbank.output_power}})

            influx_write_event = InfluxWriteEvent("home", "solix", json.dumps(influx_data))
            self.mqtt_publish("influx/write", influx_write_event.to_json(), namespace="mqtt")
        except Exception as e:
            self.log("SolixClientApp :: MQTT message :: Error in MQTT message received: {}".format(e), level="ERROR")
