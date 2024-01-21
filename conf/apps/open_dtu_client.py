from appdaemon.plugins.mqtt.mqttapi import Mqtt
import json
from model.influx_write_event import InfluxWriteEvent


class OpenDtuClientApp(Mqtt):
    def initialize(self):
        self.set_namespace("mqtt")
        self.mqtt_subscribe("solar/#")
        self.listen_event(self.mqtt_message_received_event)

    def mqtt_message_received_event(self, event_name, data, kwargs):
        try:
            # check if data is a mqtt message
            if not data.get("topic"):
                return
            if len(data) == 0:
                self.log("OpenDtuClientApp :: MQTT message :: Received with no data", level="WARNING")
                return

            # split the topic in parts
            topic_parts = data.get("topic").split("/")
            # check if the topic contains a number at position 1 (solar/112183830158/1/name)
            if topic_parts[1].isdigit() and topic_parts[2].isdigit() and topic_parts[3] != "name":
                influx_data = []
                influx_data.append({"measurement": topic_parts[2], "tags": {}, "fields": {topic_parts[3]: data.get("payload")}})

                influx_write_event = InfluxWriteEvent("home", "solar", json.dumps(influx_data))
                self.mqtt_publish("influx/write", influx_write_event.to_json(), namespace="mqtt")

        except Exception as e:
            self.log("OpenDtuClientApp :: MQTT message :: Error in MQTT message received: {}".format(e), level="ERROR")
