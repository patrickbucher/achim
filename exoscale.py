from exoscale_auth import ExoscaleV2Auth
import requests


class Exoscale:
    def __init__(self, config):
        self.auth = ExoscaleV2Auth(
            config["EXOSCALE_API_KEY"], config["EXOSCALE_API_SECRET"]
        )
        url_prefix = f"{config['EXOSCALE_ENVIRONMENT']}-{config['EXOSCALE_ZONE']}"
        self.base_url = f"https://{url_prefix}.exoscale.com/v2"

    def get_template_by_name(self, name):
        templates = self.get("template").json()["templates"]
        matches = filter(lambda t: t["name"] == name, templates)
        return next(matches)

    def suffix_url(self, suffix):
        return f"{self.base_url}/{suffix}"

    def get(self, suffix):
        headers = {"Content-Type": "application/json"}
        url = self.suffix_url(suffix)
        return requests.get(url, auth=self.auth, headers=headers)
