
from dataclasses import dataclass
from typing import Any

import json

@dataclass
class InfluxWriteEvent:
    """Start Wakeup Event Class - Event Data is passed from the automation framework to the app via event trigger"""

    org: str
    bucket: str
    data: dict

    @staticmethod
    def from_dict(obj: Any) -> "InfluxWriteEvent":
        """Converts the event data into a class"""
        
        _org = str(obj.get("org"))
        _bucket = str(obj.get("bucket"))
        _data = obj.get("data")
        return InfluxWriteEvent(_org, _bucket, _data)
    
    def to_dict(self) -> dict:
        """Converts the class into a dictionary"""
        
        return {"org": self.org, "bucket": self.bucket, "data": self.data}
    
    def to_json(self) -> str:
        """Converts the class into a json string"""

        return json.dumps(self.to_dict())
    