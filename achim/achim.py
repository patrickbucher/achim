import sys
from functools import reduce

import click
from dotenv import dotenv_values
from achim.exoscale import Exoscale
from jinja2 import Template
import yaml

from achim.utils import is_valid_ipv4, parse_label_value_arg

sizes = ["micro", "tiny", "small", "medium", "large", "extra-large"]
instance_type_filter = {
    "authorized": True,
    "family": "standard",
}
default_image = "Linux Debian 13 (Trixie) 64-bit"
default_user_name = "user"


@click.group(help="Manage Exoscale Compute Instances")
@click.pass_context
def cli(ctx):
    config = dotenv_values(".env")
    keys = [
        "EXOSCALE_API_KEY",
        "EXOSCALE_API_SECRET",
        "EXOSCALE_ZONE",
    ]
    if any(filter(lambda k: k not in config, keys)):
        fatal("missing settings in .env file (see sample.env)")

    ctx.ensure_object(dict)
    ctx.obj["exo"] = Exoscale(config)


@cli.command(help="List Images")
@click.option("--contains", help="filter image name (case insentitive)", default="")
@click.pass_context
def list_images(ctx, contains):
    for name in get_image_names(ctx, contains):
        print(name)


@cli.command(help="List Instances by Label/Value Selectors")
@click.option("--by", help="label=value pairs selector")
@click.pass_context
def list_instances(ctx, by):
    exo = ctx.obj["exo"]
    selectors = parse_label_value_arg(by)
    for instance in exo.get_instances_by(selectors):
        info = extract_instance_info(instance, ["id", "name", "state", "labels"])
        print(info)


@cli.command(help="Create a Compute Instance")
@click.option("--name", required=True, help="instance name (hostname)")
@click.option("--keyname", required=True, help="name of registered SSH key")
@click.option("--context", help="context (label)", default="default")
@click.option("--group", help="group (label)", default="default")
@click.option("--owner", help="owner (label)", default="default")
@click.option("--autostart", help="automatically start VM", is_flag=True, default=False)
@click.option("--image", help="image name", default=default_image)
@click.option("--size", help="instance size", default="micro")
@click.option(
    "--cloud-init", type=click.File("r", encoding="utf-8"), help="cloud init YAML file"
)
@click.pass_context
def create_instance(
    ctx,
    name,
    keyname,
    context,
    group,
    owner,
    autostart,
    image,
    size,
    cloud_init,
):
    must_be_valid_image(ctx, image)
    must_be_valid_size(size)
    cloud_init_data = {}
    if cloud_init:
        cloud_init_data = yaml.load(cloud_init, yaml.SafeLoader)
    exo = ctx.obj["exo"]
    existing = exo.get_instances()
    if any([instance["name"] == name for instance in existing]):
        fatal(f"name '{name}' is already in use")
    instance = do_create_instance(
        exo,
        name,
        keyname,
        context,
        group,
        owner,
        autostart,
        image,
        size,
        cloud_init_data=cloud_init_data,
    )
    print(instance)


@cli.command(help="Start Compute Instances by Label/Value Selectors")
@click.option("--by", help="label=value pairs selector")
@click.pass_context
def start(ctx, by):
    exo = ctx.obj["exo"]
    selectors = parse_label_value_arg(by)
    for instance in exo.get_instances_by(selectors):
        print(exo.start_instance(instance["id"]))


@cli.command(help="Stop Compute Instances by Label/Value Selectors")
@click.option("--by", help="label=value pairs selector")
@click.pass_context
def stop(ctx, by):
    exo = ctx.obj["exo"]
    selectors = parse_label_value_arg(by)
    for instance in exo.get_instances_by(selectors):
        print(exo.stop_instance(instance["id"]))


@cli.command(help="Destroy Compute Instances by Label/Value Selectors")
@click.option("--by", help="label=value pairs selector")
@click.option("--sure", is_flag=True, prompt=True, default=False, help="Are you sure?")
@click.pass_context
def destroy(ctx, by, sure):
    if not sure:
        return
    exo = ctx.obj["exo"]
    selectors = parse_label_value_arg(by)
    for instance in exo.get_instances_by(selectors):
        print(exo.destroy_instance(instance["id"]))


@cli.command(help="Enable Instance Protection by Label/Value Selectors")
@click.option("--by", help="label=value pairs selector")
@click.pass_context
def protect(ctx, by):
    exo = ctx.obj["exo"]
    selectors = parse_label_value_arg(by)
    for instance in exo.get_instances_by(selectors):
        print(exo.protect_instance(instance["id"]))


@cli.command(help="Revoke Instance Protection by Label/Value Selectors")
@click.option("--by", help="label=value pairs selector")
@click.option("--sure", is_flag=True, prompt=True, default=False, help="Are you sure?")
@click.pass_context
def deprotect(ctx, by, sure):
    if not sure:
        return
    exo = ctx.obj["exo"]
    selectors = parse_label_value_arg(by)
    for instance in exo.get_instances_by(selectors):
        print(exo.deprotect_instance(instance["id"]))


@cli.command(help="Create Compute Instances for a Group")
@click.option(
    "--file", type=click.File("r", encoding="utf-8"), help="groups file to be used"
)
@click.option("--context", help="context (label)", default="default")
@click.option("--keyname", required=True, help="name of registered SSH key")
@click.option("--autostart", help="automatically start VM", is_flag=True, default=False)
@click.option("--image", help="image name", default=default_image)
@click.option("--size", help="instance size", default="micro")
@click.option(
    "--ignore-existing",
    help="create group even if vms from it already exists",
    is_flag=True,
    default=False,
)
@click.pass_context
def create_group(ctx, file, keyname, context, autostart, image, size, ignore_existing):
    must_be_valid_image(ctx, image)
    must_be_valid_size(size)
    exo = ctx.obj["exo"]
    existing = exo.get_instances()
    group = yaml.load(file.read(), Loader=yaml.SafeLoader)
    group_name = sanitize_name(group["name"])
    users = group["users"]
    host_names = {to_host_name(u["name"]) for u in users}
    existing_names = {e["name"] for e in existing}
    already_used = host_names.intersection(existing_names)
    if already_used and not ignore_existing:
        fatal(f"names '{already_used}' are already in use")
    instances = []
    for user in users:
        host_name = to_host_name(user["name"])
        owner_name = user["name"]
        if host_name in already_used and ignore_existing:
            continue
        cloud_init_data = {}
        if "cloud-config" in group:
            cloud_init_data = prepare_cloud_init_data(group["cloud-config"], user)
        instance = do_create_instance(
            exo,
            host_name,
            keyname,
            context,
            group_name,
            owner_name,
            autostart,
            image=image,
            size=size,
            cloud_init_data=cloud_init_data,
        )
        instances.append(instance)
    print(instances)


@cli.command(help="Create Scenario Instances for a Group")
@click.option(
    "--scenario",
    type=click.File("r", encoding="utf-8"),
    help="scenario file to be used",
)
@click.option(
    "--group", type=click.File("r", encoding="utf-8"), help="groups file to be used"
)
@click.option("--context", help="context (label)", default="default")
@click.option("--keyname", required=True, help="name of registered SSH key")
@click.option(
    "--autostart", help="automatically start VMs", is_flag=True, default=False
)
@click.pass_context
def create_scenario(ctx, scenario, group, context, keyname, autostart):
    scenario_data = yaml.load(scenario.read(), Loader=yaml.SafeLoader)
    group_data = yaml.load(group.read(), Loader=yaml.SafeLoader)
    exo = ctx.obj["exo"]
    validate_scenario(ctx, scenario_data)
    instance_data = scenario_data["instances"]
    network_data = scenario_data["networks"]
    group_name = sanitize_name(group_data["name"])
    user_data = group_data["users"]
    instances_by_username = determine_instances(instance_data, user_data)
    networks_by_username = determine_networks(
        network_data, user_data, instances_by_username
    )
    instances = [
        do_create_instance(
            exo,
            to_host_name(instance_data["canonical_name"]),
            keyname,
            context,
            group_name,
            username,
            autostart,
            image=instance_data["image"],
            size=instance_data["size"],
            additional_labels={"scenario": scenario_data["name"]},
        )
        for username, instances in instances_by_username.items()
        for instance_data in instances
    ]
    print(instances)
    networks = [
        exo.create_network(
            to_host_name(network_data["canonical_name"]),
            start_ip=network_data["start-ip"],
            end_ip=network_data["end-ip"],
            netmask=network_data["netmask"],
            labels={"scenario": scenario_data["name"], "owner": username},
        )
        for username, networks in networks_by_username.items()
        for network_data in networks
    ]
    print(networks)
    attachments = [
        exo.attach_network(a["network_id"], a["instance_id"], a["ip"])
        for a in determine_attachments(exo, networks_by_username)
    ]
    print(attachments)


@click.option("--ip", help="Attach with static IP Address")
@click.pass_context
def attach_network(ctx, network, instance, ip):
    must_be_valid_name(network)
    must_be_valid_name(instance)
    if ip:
        must_be_valid_ipv4(ip)
    exo = ctx.obj["exo"]
    instances = list(filter(lambda i: i["name"] == instance, exo.get_instances()))
    networks = list(filter(lambda n: n["name"] == network, exo.get_networks()))
    if len(networks) != 1:
        fatal(f"network '{network}' not found or not unique")
    if len(instances) != 1:
        fatal(f"instance '{instance}' not found or not unique")
    network_id = networks[0]["id"]
    instance_id = instances[0]["id"]
    print(exo.attach_network(network_id, instance_id, ip))


@cli.command(help="Destroy a Private Network")
@click.option("--name", help="Name of the Network", required=True)
@click.pass_context
def destroy_network(ctx, name):
    must_be_valid_name(name)
    exo = ctx.obj["exo"]
    networks = list(filter(lambda n: n["name"] == name, exo.get_networks()))
    if len(networks) != 1:
        fatal(f"network '{name}' not found or not unique")
    print(exo.delete_network(networks[0]["id"]))


@cli.command(help="Destroy all Private Networks")
@click.option("--sure", is_flag=True, prompt=True, default=False, help="Are you sure?")
@click.pass_context
def destroy_all_networks(ctx, sure):
    if not sure:
        return
    exo = ctx.obj["exo"]
    for network in exo.get_networks():
        print(exo.delete_network(network["id"]))


# TODO: consider label/value selection (all instances if not restricted)
@cli.command(help="Add Label to all Instances")
@click.option("--key", help="Key of the Label", required=True)
@click.option("--value", help="Value of the Label", required=True)
@click.pass_context
def add_label(ctx, key, value):
    exo = ctx.obj["exo"]
    if not key or not value:
        fatal("key and value required")
    instances = exo.get_instances()
    for instance in instances:
        existing = instance.get("labels", {})
        print(
            exo.update_instance_labels(instance["id"], labels={**existing, key: value})
        )


@cli.command(help="Flush all non-system DNS Records of a Domain")
@click.option("--domain", help="Domain to be Flushed", required=True)
@click.option("--sure", is_flag=True, prompt=True, default=False, help="Are you sure?")
@click.pass_context
def flush_dns(ctx, domain, sure):
    if not sure:
        return
    exo = ctx.obj["exo"]
    domain_id = exo.get_domain_id(domain)
    records = exo.get_non_system_dns_records(domain_id)
    record_ids = map(lambda r: r.get("id", ""), records)
    for record_id in record_ids:
        print(exo.delete_dns_record(domain_id, record_id))


@cli.command(help="Sync VM hostnames with DNS records for a Domain")
@click.option("--domain", help="Domain to be Flushed", required=True)
@click.pass_context
def sync_dns(ctx, domain):
    exo = ctx.obj["exo"]
    ips_hostnames = [(i["public-ip"], i["name"]) for i in exo.get_instances()]
    domain_id = exo.get_domain_id(domain)
    records = exo.get_non_system_dns_records(domain_id)
    existing = set([(r["content"], r["name"]) for r in records])
    required = set(ips_hostnames)
    to_be_deleted = existing - required
    to_be_created = required - existing
    for ip, _name in to_be_deleted:
        matches = filter(lambda r: r["content"] == ip, records)
        matching_ids = map(lambda r: r["id"], matches)
        for id in matching_ids:
            print("deleted", exo.delete_dns_record(domain_id, id))
    for ip, name in to_be_created:
        print("created", exo.create_dns_record(domain_id, name, ip, ttl=300))


@cli.command(help="Check Instance State for Label/Value Selectors")
@click.option("--by", help="label=value pairs selector")
@click.pass_context
def state(ctx, by):
    exo = ctx.obj["exo"]
    selectors = parse_label_value_arg(by)
    for instance in exo.get_instances_by(selectors):
        print(extract_instance_info(instance, ["name", "state"]))


def do_create_instance(
    exo,
    name,
    keyname,
    context="",
    group="",
    owner="",
    autostart=False,
    image="",
    size="",
    additional_labels={},
    cloud_init_data={},
):
    template = exo.get_template_by_name(image)
    instance_types = exo.get_instance_types(instance_type_filter)
    smallest = list(filter(lambda it: it["size"] == size, instance_types))[0]
    ssh_key = exo.get_ssh_key(keyname)
    labels = {
        "name": name,
        "context": context,
        "group": group,
        "owner": owner,
        **additional_labels,
    }
    labels = {k: v for (k, v) in labels.items() if v}
    return exo.create_instance(
        name,
        template,
        smallest,
        ssh_key,
        labels,
        autostart,
        cloud_init_data=cloud_init_data,
    )


def get_image_names(ctx, contains=""):
    exo = ctx.obj["exo"]
    templates = exo.list_templates()
    names = sorted(map(lambda t: t["name"], templates))
    if contains:
        names = filter(lambda n: contains.strip().lower() in n.lower(), names)
    return list(names)


def get_networks(ctx, contains=""):
    exo = ctx.obj["exo"]
    nets = exo.get_networks()
    if contains:
        nets = filter(lambda n: contains.strip().lower() in n["name"].lower(), nets)
    return list(nets)


def validate_scenario(ctx, scenario_data):
    for field in ["name", "instances"]:
        if field not in scenario_data:
            fatal(f"missing required field '{field}' in scenario file")
    instance_data = scenario_data["instances"]
    required_images = set(map(lambda i: i["image"], instance_data))
    available_images = set(get_image_names(ctx))
    missing_images = required_images - available_images
    if missing_images:
        fatal(f"no such image(s): {missing_images}")
    required_sizes = set(map(lambda i: i["size"], instance_data))
    missing_sizes = required_sizes - set(sizes)
    if missing_sizes:
        fatal(f"no such size(s): {missing_sizes}")


def determine_instances(instance_data, user_data):
    def with_canonical_hostname(entry):
        instance_name = entry["instance"]["name"]
        user_name = entry["user"]["name"]
        return {
            "name": instance_name,
            "canonical_name": to_host_name(f"{instance_name}_{user_name}"),
            "size": entry["instance"]["size"],
            "image": entry["instance"]["image"],
        }

    instances_needed = [
        {"instance": i, "user": u} for i in instance_data for u in user_data
    ]
    return {
        u["name"]: [
            with_canonical_hostname(e)
            for e in instances_needed
            if e["user"]["name"] == u["name"]
        ]
        for u in user_data
    }


def determine_networks(network_data, user_data, instances_by_username):
    def with_canonical_netname(entry, instances_by_username):
        network_name = entry["network"]["name"]
        user_name = entry["user"]["name"]
        connect_hosts = entry["network"]["connects"]
        host_ips = {e["name"]: e["ip"] for e in connect_hosts}
        net = entry["network"]
        ip_config = {
            "netmask": net.get("netmask", ""),
            "start-ip": net.get("start-ip", ""),
            "end-ip": net.get("end-ip", ""),
        }
        ip_config = ip_config if all(ip_config.values()) else {}
        return {
            **ip_config,
            "name": network_name,
            "canonical_name": to_host_name(f"{network_name}_{user_name}"),
            "connects": [
                {
                    "canonical_name": instance["canonical_name"],
                    "ip": host_ips[instance["name"]],
                }
                for instance_username, instances in instances_by_username.items()
                for instance in instances
                if instance["name"] in host_ips.keys()
                and instance_username == user_name
            ],
        }

    networks_needed = [
        {"network": n, "user": u} for n in network_data for u in user_data
    ]
    return {
        u["name"]: [
            with_canonical_netname(e, instances_by_username)
            for e in networks_needed
            if e["user"]["name"] == u["name"]
        ]
        for u in user_data
    }


def determine_attachments(exo, networks_by_username):
    networks = exo.get_networks()
    instances = exo.get_instances()
    all_networks = reduce(lambda acc, e: acc + e, networks_by_username.values())
    attachments = []
    for network_data in all_networks:
        name = network_data["canonical_name"]
        connects = network_data["connects"]
        network = next(filter(lambda n: n["name"] == name, networks))
        network_id = network["id"]
        for connect in connects:
            instance_id = next(
                filter(lambda i: i["name"] == connect["canonical_name"], instances)
            )["id"]
            attachments.append(
                {
                    "network_id": network_id,
                    "instance_id": instance_id,
                    "ip": connect["ip"],
                }
            )
    return attachments


def to_host_name(name):
    return name.replace(".", "-").replace("_", "-")


def sanitize_name(name):
    return name.lower().replace(" ", "-")


def must_be_valid_size(size):
    if not size in sizes:
        fatal(f"no such size '{size}', use one of {sizes}")


def must_be_valid_image(ctx, image):
    if not is_available_image(ctx, image):
        fatal(f"no such image '{image}, use list-images to see available images")


def must_be_valid_name(name):
    if not sanitize_name(name):
        fatal(f"{name} is not a valid name")


def must_be_valid_ipv4(ip):
    if not is_valid_ipv4(ip):
        fatal(f"{ip} is not a valid IPv4 address")


def is_available_image(ctx, name):
    return name in get_image_names(ctx)


def eprint(message):
    print(message, file=sys.stderr)


def fatal(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def extract_instance_info(instance, fields):
    info = {}
    for key in fields:
        info[key] = instance.get(key, "")
    return info


def prepare_cloud_init_data(cloud_config={}, data={}):
    template = Template(yaml.dump(cloud_config))
    cloud_init_data = yaml.load(template.render(data), yaml.SafeLoader)
    return cloud_init_data
