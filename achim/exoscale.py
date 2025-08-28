from exoscale_auth import ExoscaleV2Auth
import requests


class Exoscale:
    def __init__(self, config):
        self.auth = ExoscaleV2Auth(
            config["EXOSCALE_API_KEY"], config["EXOSCALE_API_SECRET"]
        )
        url_prefix = f"api-{config['EXOSCALE_ZONE']}"
        self.base_url = f"https://{url_prefix}.exoscale.com/v2"

    def list_templates(self):
        return self.get("template").json()["templates"]

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
        return self.get("instance").json()["instances"]

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
        bytes_to_gb = lambda b: int(b / 1024**3)
        payload = {
            "auto-start": autostart,
            "name": name,
            "instance-type": instance_type,
            "template": template,
            "ssh-key": {"name": ssh_key["name"]},
            "disk-size": bytes_to_gb(template["size"]) if "size" in template else 10,
            "labels": labels,
        }
        return self.post("instance", payload).json()

    def create_network(
        self,
        name,
        start_ip="10.0.0.1",
        end_ip="10.0.0.150",
        netmask="255.255.255.0",
        description="",
        labels={},
    ):
        payload = {
            "name": name,
            "start-ip": start_ip,
            "end-ip": end_ip,
            "netmask": netmask,
            "description": description,
            "labels": labels,
        }
        payload = {k: v for k, v in payload.items() if v}
        return self.post("private-network", payload).json()

    def get_networks(self):
        return self.get("private-network").json()["private-networks"]

    def attach_network(self, network, instance, ip):
        payload = {
            "ip": ip,
            "instance": {
                "id": instance,
            },
        }
        payload = {k: v for k, v in payload.items() if v}
        return self.put(f"private-network/{network}:attach", payload).json()

    def delete_network(self, network):
        return self.delete(f"private-network/{network}").json()

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
