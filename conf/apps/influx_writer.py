from appdaemon.plugins.mqtt.mqttapi import Mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from model.influx_write_event import InfluxWriteEvent

from dotenv import load_dotenv

import os
import requests
import json

# Load environment variables from .env file
load_dotenv()


class InfluxConfig:
    """InfluxDB Config Class"""

    def __init__(self):
        """InfluxDB Config"""

        self.influxdb_url = os.getenv("INFLUXDB_URL", "http://192.168.178.10:8086")
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN", "TOKEN")
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "home")


class InfluxWriterApp(Mqtt):
    """"""

    def initialize(self):
        """Initialize"""

        self.influx_config = InfluxConfig()
        self.set_namespace("mqtt")
        self.mqtt_subscribe("influx/write")
        self.listen_event(self.mqtt_message_received_event)

    def create_bucket(self, bucket, org_id):
        """Create a bucket"""
        headers = {"Authorization": f"Token {self.influx_config.influxdb_token}"}
        payload = {"name": bucket, "orgID": org_id}
        response = requests.post(f"{self.influx_config.influxdb_url}/api/v2/buckets", headers=headers, json=payload, timeout=2)

        if response.status_code == 201:
            self.log(f"InfluxWriterApp :: Management :: influxdb bucket {bucket} created.", level="INFO")

        else:
            self.log(f"InfluxWriterApp :: Management :: error creating influxdb bucket {bucket}.", level="ERROR")

    def _json_object_hook(self, dct):
        # Convert numeric strings back to int or float
        for key, value in dct.items():
            if isinstance(value, str) and value.replace(".", "", 1).isdigit():
                if "." in value:
                    dct[key] = float(value)
                else:
                    dct[key] = int(value)
        return dct

    def mqtt_message_received_event(self, event_name, data, kwargs):
        """Write to Influx"""

        if not data.get("topic"):
            return
        if len(data) == 0:
            self.log("InfluxWriterApp :: MQTT message :: received with no data", level="WARNING")
            return
        if data.get("topic") != "influx/write":
            return

        influx_write_event = InfluxWriteEvent.from_dict(json.loads(data["payload"]))

        self.log(f"InfluxWriterApp :: influxdb :: write event received for org {influx_write_event.org} ;Bucket {influx_write_event.bucket}")

        client = InfluxDBClient(url=self.influx_config.influxdb_url, token=self.influx_config.influxdb_token)
        bucket_api = client.buckets_api()
        org_api = client.organizations_api()

        orgs = org_api.find_organizations()
        org = [o for o in orgs if o.name == influx_write_event.org]

        current_bucket = bucket_api.find_buckets(name=influx_write_event.bucket)

        if len(current_bucket.buckets) == 0:
            self.log(f"InfluxWriterApp :: influxdb :: bucket {influx_write_event.bucket} does not exist. creating...")
            self.create_bucket(influx_write_event.bucket, org[0].id)

        if len(current_bucket.buckets) > 1:
            self.log(f"InfluxWriterApp :: influxdb :: bucket {influx_write_event.bucket} has more than one bucket. please check.")
        else:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            data = json.loads(influx_write_event.data, object_hook=self._json_object_hook)
            write_api.write(org=influx_write_event.org, bucket=influx_write_event.bucket, record=data)

            self.log(f"InfluxWriterApp :: influxdb :: writing data to bucket {influx_write_event.bucket} successful.")
        client.close()
