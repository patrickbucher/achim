from exoscale_auth import ExoscaleV2Auth
import requests


class Exoscale:
    def __init__(self, config):
        self.auth = ExoscaleV2Auth(
            config["EXOSCALE_API_KEY"], config["EXOSCALE_API_SECRET"]
        )
        url_prefix = f"api-{config['EXOSCALE_ZONE']}"
        self.base_url = f"https://{url_prefix}.exoscale.com/v2"

    def get_template_by_name(self, name):
        templates = self.get("template").json()["templates"]
        matches = filter(lambda t: t["name"] == name, templates)
        return next(matches)

    def get_instance_types(self, rules):
        def filter_rule(instance_type, key, value):
            return instance_type[key] == value

        instance_types = self.get("instance-type").json()["instance-types"]
        filtered_types = filter(
            lambda it: all([filter_rule(it, k, v) for (k, v) in rules.items()]),
            instance_types,
        )
        return list(filtered_types)

    def get_instances(self):
        return self.get(f"instance").json()["instances"]

    def start_instance(self, id):
        return self.put(f"instance/{id}:start").json()

    def stop_instance(self, id):
        return self.put(f"instance/{id}:stop").json()

    def destroy_instance(self, id):
        return self.delete(f"instance/{id}").json()

    def get_ssh_key(self, name):
        return self.get(f"ssh-key/{name}").json()

    def get_instance_by_name(self, name):
        instances = self.get("instance").json()["instances"]
        return next(filter(lambda i: i["name"] == name, instances))

    def create_instance(
        self, name, template, instance_type, ssh_key, labels={}, autostart=False
    ):
        payload = {
            "auto-start": autostart,
            "name": name,
            "instance-type": instance_type,
            "template": template,
            "ssh-key": {"name": ssh_key["name"]},
            "disk-size": 10,
            "labels": labels,
        }
        return self.post("instance", payload).json()

    def suffix_url(self, suffix):
        return f"{self.base_url}/{suffix}"

    def get(self, suffix):
        headers = {"Content-Type": "application/json"}
        url = self.suffix_url(suffix)
        return requests.get(url, auth=self.auth, headers=headers)

    def post(self, suffix, payload):
        headers = {"Content-Type": "application/json"}
        url = self.suffix_url(suffix)
        return requests.post(url, json=payload, auth=self.auth, headers=headers)

    def put(self, suffix, payload=None):
        headers = {"Content-Type": "application/json"}
        url = self.suffix_url(suffix)
        return requests.put(url, json=payload, auth=self.auth, headers=headers)

    def delete(self, suffix):
        headers = {"Content-Type": "application/json"}
        url = self.suffix_url(suffix)
        return requests.delete(url, auth=self.auth, headers=headers)
