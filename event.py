from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Self
from zoneinfo import ZoneInfo

import pytz

SPOND_JUNIORS_GROUP = 'E1604708D52A4BF8B4583435A48C10D0'
SPOND_SENIORS_GROUP = 'E115E8334BA948D5AC3EF2EE56B54B81'

SPOND_GROUP_TO_WORDPRESS_ID = {
    SPOND_SENIORS_GROUP: 41,
    SPOND_JUNIORS_GROUP: 55,
}

@dataclass
class Event:
    spond_id: str
    status: str
    title: str
    information: str
    start: datetime
    end: datetime
    location_name: str
    location_address: str
    location_longitude: float
    location_latitude: float
    age_group_ids: list[int]

    @staticmethod
    def from_spond(spond_event):
        group_id = spond_event.get("recipients", {}).get("group", {}).get("id")

        # Don't copy full description for the Juniors
        if group_id == SPOND_JUNIORS_GROUP:
            description = "<em>This event was automatically synchronised from Spond. Please view details there.</em>"
        else:
            description = spond_event["description"] or ""
            description += "\r\n\r\n<em>This event was automatically synchronised from Spond. Please respond there.</em>"
        description = Event.__trim(description)

        cancelled = "cancelled" in spond_event and spond_event["cancelled"]

        return Event(
            spond_id=spond_event["id"],
            status="cancelled" if cancelled  else "publish",
            title=Event.__trim(spond_event["heading"]),
            information=description,
            start=Event.__from_iso_format_datetime(spond_event.get("startTimestamp")),
            end=Event.__from_iso_format_datetime(spond_event.get("endTimestamp")),
            location_name=Event.__trim(spond_event.get("location", {}).get("feature")) or "",
            location_address=Event.__trim(spond_event.get("location", {}).get("address")) or "",
            location_longitude=Event.__to_float(spond_event.get("location", {}).get("longitude")),
            location_latitude=Event.__to_float(spond_event.get("location", {}).get("latitude")),
            age_group_ids= [i for i in [SPOND_GROUP_TO_WORDPRESS_ID.get(group_id)] if i is not None]
        )

    @staticmethod
    def from_wordpress(fixture):
        acf = fixture.get("acf", {})
        if acf.get("external_link_text") == "Spond":
            spond_id = acf.get("external_link", "").split("/")[-1]
        else:
            spond_id = None

        start_timestamp = Event.__datetime_from_wordpress(acf.get("start_date"), acf.get("start_time") or "00:00:00")
        end_timestamp = Event.__datetime_from_wordpress(acf.get("end_date"), acf.get("end_time") or "00:00:00")

        location = acf.get("location") or {}
        return Event(
            spond_id=spond_id,
            status="publish",
            title=fixture.get("title", {}).get("rendered"),
            information=acf.get("information"),
            start=start_timestamp,
            end=end_timestamp,
            location_name=location.get("name") or "",
            location_address=location.get("address") or "",
            location_longitude=Event.__to_float(location.get("lng")),
            location_latitude=Event.__to_float(location.get("lat")),
            age_group_ids= fixture.get("fixture-age", [])
        )

    @staticmethod
    def __datetime_from_wordpress(date_string, time_string: str | Any) -> Optional[datetime]:
        if not date_string:
            return None
        london = pytz.timezone("Europe/London")
        london_datetime = london.localize(datetime(int(date_string[0:4]), int(date_string[4:6]), int(date_string[6:8]),
                                                  int(time_string[0:2]), int(time_string[3:5])))
        return london_datetime.astimezone(timezone.utc)

    @staticmethod
    def __from_iso_format_datetime(value: str):
        if value:
            return datetime.fromisoformat(value)
        else:
            return None

    @staticmethod
    def __to_float(value):
        if value is None:
            return None
        return float(value)

    @staticmethod
    def __trim(value: str):
        if value is None:
            return None
        return value.strip()

    def is_modified(self, other):
        result = self.title != other.title or self.information != other.information or \
                 self.start != other.start or self.end != other.end or \
                 self.location_name != other.location_name or self.location_address != other.location_address or \
                 self.location_longitude != other.location_longitude or self.location_latitude != other.location_latitude or \
                 self.age_group_ids != other.age_group_ids
        return result

    def to_wordpress(self, wordpress_id, existing_wordpress: Optional[Self]):

        local_start = self.start.astimezone(ZoneInfo('Europe/London'))
        local_end = self.end.astimezone(ZoneInfo('Europe/London'))

        if self.location_name == "" and self.location_address == "":
            location = None
        else:
            location = {
                "name": self.location_name,
                "address": self.location_address,
                "lng": self.location_longitude,
                "lat": self.location_latitude,
                "zoom": 17
            }

        # Preserve any groups that we are not interested in
        age_group_ids = set()
        if existing_wordpress:
            age_group_ids.update(existing_wordpress.age_group_ids)
            age_group_ids.discard(SPOND_GROUP_TO_WORDPRESS_ID.values())
        age_group_ids.update(self.age_group_ids)

        return {
            "id": wordpress_id,
            "status": "publish",
            "title": self.title,
            "fixture-age": list(age_group_ids),
            "acf": {
                "information": self.information,
                "start_date": local_start.strftime("%Y%m%d") if local_start else None,
                "start_time": local_start.strftime("%H:%M") if local_start else None,
                "end_date": local_end.strftime("%Y%m%d") if local_end else None,
                "end_time": local_end.strftime("%H:%M") if local_end else None,
                "location": location,
                "show_external_button": True,
                "external_link_text": "Spond",
                "external_link": f"https://spond.com/client/sponds/{self.spond_id}"
            }
        }



