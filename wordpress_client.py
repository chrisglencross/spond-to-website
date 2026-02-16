import logging
import requests
from requests.auth import HTTPBasicAuth

class WordPressClient:

    logger = logging.getLogger('WordPressClient')

    def __init__(self, username, password):
        self.hostname = "www.epsomandewellharriers.org"
        self.auth = HTTPBasicAuth(username, password)

    def get_fixtures(self):
        page=1
        fixtures=[]
        while True:
            response = requests.get(f"https://{self.hostname}/wp-json/wp/v2/fixture/",
                                    params=f"per_page=100&page={page}",
                                    auth=self.auth,
                                    headers={
                                        "Accept": "application/json",
                                        "User-Agent": "SyncFromSpond"
                                    })
            response.raise_for_status()
            fixtures.extend(response.json())
            if page >= int(response.headers['X-WP-TotalPages']) or page > 10:
                break
            page += 1
        return fixtures

    def insert(self, fixture):
        self.logger.info(f"Inserting {fixture.title} (Spond {fixture.spond_id})")
        response = requests.post(f"https://{self.hostname}/wp-json/wp/v2/fixture/",
                                auth=self.auth,
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                    "User-Agent": "SyncFromSpond"
                                },
                                json=fixture.to_wordpress(None))
        response.raise_for_status()

    def update(self, wordpress_id, fixture):
        self.logger.info(f"Updating {fixture.title} [{wordpress_id}] (Spond {fixture.spond_id})")
        response = requests.put(f"https://{self.hostname}/wp-json/wp/v2/fixture/{wordpress_id}",
                     auth=self.auth,
                     headers={
                         "Content-Type": "application/json",
                         "Accept": "application/json",
                         "User-Agent": "SyncFromSpond"
                     },
                     json=fixture.to_wordpress(wordpress_id))
        response.raise_for_status()

    def delete(self, wordpress_id, fixture):
        self.logger.info(f"Deleting {fixture.title} [{wordpress_id}] (Spond {fixture.spond_id})")
        response = requests.delete(f"https://{self.hostname}/wp-json/wp/v2/fixture/{wordpress_id}",
                                auth=self.auth,
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                    "User-Agent": "SyncFromSpond"
                                })
        response.raise_for_status()
