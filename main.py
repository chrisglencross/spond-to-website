#!/usr/bin/env python3

import asyncio
import logging
from datetime import datetime, timezone
import yaml
from spond import spond

from event import Event
from wordpress_client import WordPressClient


FORMAT = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)

logger = logging.getLogger('main')

async def main():

    with open(".config.yaml", "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)

    now = datetime.now(timezone.utc)

    wordpress_client = WordPressClient(username=config["wordpress"]["username"], password=config["wordpress"]["password"])
    spond_client = spond.Spond(username=config["spond"]["username"], password=config["spond"]["password"])

    wordpress_fixtures_by_wordpress_id = {f["id"]: wpf for f in wordpress_client.get_fixtures() if (wpf := Event.from_wordpress(f)).spond_id}
    wordpress_id_by_spond_id = {value.spond_id: key for key, value in wordpress_fixtures_by_wordpress_id.items()}
    logger.info(f"Loaded {len(wordpress_id_by_spond_id)} fixtures from WordPress")

    spond_events = {e["id"]: Event.from_spond(e) for e in await spond_client.get_events(group_id="E115E8334BA948D5AC3EF2EE56B54B81", include_scheduled=True, include_hidden=True, min_start=now)}
    await spond_client.clientsession.close()
    logger.info(f"Loaded {len(spond_events)} events from Spond")

    # Update or delete existing fixtures unless they are in the past
    for wordpress_id, wordpress_fixture in wordpress_fixtures_by_wordpress_id.items():
        latest_from_spond = spond_events.get(wordpress_fixture.spond_id)
        if not latest_from_spond or latest_from_spond.status == 'cancelled':
            # Don't delete events that are in the past
            if wordpress_fixture.start > now:
                wordpress_client.delete(wordpress_id, wordpress_fixture)
        elif wordpress_fixture.is_modified(latest_from_spond):
            wordpress_client.update(wordpress_id, latest_from_spond)

    for spond_id, spond_event in spond_events.items():
        if spond_id not in wordpress_id_by_spond_id.keys() and spond_event.start > now:
            wordpress_client.insert(spond_event)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
asyncio.run(main())