import sys
from functools import reduce

import click
from dotenv import dotenv_values
from achim.exoscale import Exoscale
from jinja2 import Environment, PackageLoader, select_autoescape
import requests
import yaml

from achim.utils import is_valid_ipv4

sizes = ["micro", "tiny", "small", "medium", "large", "extra-large"]
instance_type_filter = {
    "authorized": True,
    "family": "standard",
}
default_image = "Linux Debian 13 (Trixie) 64-bit"
default_user_name = "user"


@click.group(help="Manage Exoscale Compute Instances for Groups")
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


@cli.command(help="Start a Compute Instance")
@click.option("--name", help="instance name (hostname)")
@click.pass_context
def start_instance(ctx, name):
    exo = ctx.obj["exo"]
    instance = exo.get_instance_by_name(name)
    print(exo.start_instance(instance["id"]))


@cli.command(help="Stop a Compute Instance")
@click.option("--name", help="instance name (hostname)")
@click.pass_context
def stop_instance(ctx, name):
    exo = ctx.obj["exo"]
    instance = exo.get_instance_by_name(name)
    print(exo.stop_instance(instance["id"]))


@cli.command(help="Destroy a Compute Instance")
@click.option("--name", help="instance name (hostname)")
@click.option("--sure", is_flag=True, prompt=True, default=False, help="Are you sure?")
@click.pass_context
def destroy_instance(ctx, name, sure):
    if not sure:
        return
    exo = ctx.obj["exo"]
    instance = exo.get_instance_by_name(name)
    print(exo.destroy_instance(instance["id"]))


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
        )
        instances.append(instance)
    print(instances)


@cli.command(help="Start Compute Instances for a Group")
@click.option("--name", help="group name")
@click.pass_context
def start_group(ctx, name):
    exo = ctx.obj["exo"]
    instances = exo.get_instances()
    instances = [i for i in instances if i["labels"].get("group", "") == name]
    for instance in instances:
        print(exo.start_instance(instance["id"]))


@cli.command(help="Stop Compute Instances for a Group")
@click.option("--name", help="group name")
@click.pass_context
def stop_group(ctx, name):
    exo = ctx.obj["exo"]
    instances = exo.get_instances()
    instances = [i for i in instances if i["labels"].get("group", "") == name]
    for instance in instances:
        print(exo.stop_instance(instance["id"]))


@cli.command(help="Destroy Compute Instances for a Group")
@click.option("--name", help="group name")
@click.option("--sure", is_flag=True, prompt=True, default=False, help="Are you sure?")
@click.pass_context
def destroy_group(ctx, name, sure):
    if not sure:
        return
    exo = ctx.obj["exo"]
    instances = exo.get_instances()
    instances = [i for i in instances if i["labels"].get("group", "") == name]
    for instance in instances:
        print(exo.destroy_instance(instance["id"]))


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


@cli.command(help="Stop all Instances by Scenario Name")
@click.option("--name", help="scenario name (see scenario file)")
@click.pass_context
def stop_scenario(ctx, name):
    exo = ctx.obj["exo"]
    if not name:
        fatal("scenario name required")
    instances = exo.get_instances()
    scenario_instances = list(
        filter(lambda i: i.get("labels", {}).get("scenario", "") == name, instances)
    )
    if not scenario_instances:
        fatal(f"no instances for scenario '{name}' found")
    for instance in scenario_instances:
        exo.stop_instance(instance["id"])
        print(f'stopped instance {instance["name"]}')


@cli.command(help="Start all Instances by Scenario Name")
@click.option("--name", help="scenario name (see scenario file)")
@click.pass_context
def start_scenario(ctx, name):
    exo = ctx.obj["exo"]
    if not name:
        fatal("scenario name required")
    instances = exo.get_instances()
    scenario_instances = list(
        filter(lambda i: i.get("labels", {}).get("scenario", "") == name, instances)
    )
    if not scenario_instances:
        fatal(f"no instances for scenario '{name}' found")
    for instance in scenario_instances:
        exo.start_instance(instance["id"])
        print(f'started instance {instance["name"]}')


@cli.command(help="Destroy Scenario Instances and Networks by Scenario Name")
@click.option("--name", help="scenario name (see scenario file)")
@click.option("--sure", is_flag=True, prompt=True, default=False, help="Are you sure?")
@click.pass_context
def destroy_scenario(ctx, name, sure):
    if not sure:
        return
    exo = ctx.obj["exo"]

    def has_scenario(o):
        return o["labels"].get("scenario", "") == name

    instances = [
        exo.destroy_instance(instance["id"])
        for instance in filter(has_scenario, exo.get_instances())
    ]
    networks = [
        exo.delete_network(network["id"])
        for network in filter(has_scenario, exo.get_networks())
    ]
    print(instances)
    print(networks)


@cli.command(help="Generate HTML Overview Page for a Scenario")
@click.option("--name", help="scenario name (see scenario file)")
@click.option("--hide-password", is_flag=True, default=False, help="Hide Password")
@click.option("--file", type=click.File("w", encoding="utf-8"), help="HTML output file")
@click.pass_context
def scenario_overview(ctx, name, hide_password, file):
    exo = ctx.obj["exo"]
    if not name:
        fatal("scenario name required")
    instances = list(
        filter(
            lambda i: i.get("labels", {}).get("scenario", "") == name,
            exo.get_instances(),
        )
    )
    if not instances:
        fatal(f"no instances for scenario '{name}' found")
    overview_data = []
    for instance in instances:
        labels = instance.get("labels", {})
        id = instance["id"]
        pw = exo.get_instance_password(id)
        template_id = instance.get("template", {}).get("id", "")
        template = exo.get_template(template_id) if template_id else {}
        family = template.get("family", "")
        default_user = template.get("default-user", "")
        ip = instance.get("public-ip", "")
        connect = ("rdp" if family == "windows" else "ssh") + f" {default_user}@{ip}"
        data = {
            "owner": labels.get("owner", ""),
            "name": instance["name"],
            "image": template.get("name", ""),
            "ip": ip,
            "user": default_user,
            "password": pw if not hide_password else "********",
            "connect": connect,
        }
        overview_data.append(data)
    overview_data = sorted(overview_data, key=lambda o: o["name"])
    overview_data = sorted(overview_data, key=lambda o: o["owner"])
    env = Environment(loader=PackageLoader("achim"), autoescape=select_autoescape())
    template = env.get_template("scenario.html")
    file.write(template.render(instances=overview_data, name=name))


@cli.command(help="Tests an HTTP Service on the Instances of the Group")
@click.option("--name", help="group name")
@click.option("--suffix", help="URL suffix", default="")
@click.pass_context
def probe(ctx, name, suffix):
    exo = ctx.obj["exo"]
    instances = exo.get_instances()
    instances = [i for i in instances if i["labels"].get("group", "") == name]
    for instance in instances:
        ip = instance["public-ip"]
        owner = instance["labels"]["owner"]
        url = f"http://{ip}/{suffix}"
        try:
            res = requests.get(url)
            status = res.status_code
        except Exception:
            status = "ERR"
        print(f"{ip}\t{status}\t{owner}")


@cli.command(help="Generate an Ansible Inventory by Instance Labels")
@click.option(
    "--file",
    type=click.File("w", encoding="utf-8"),
    help="inventory file to be written",
)
@click.pass_context
def inventory(ctx, file):
    exo = ctx.obj["exo"]
    instances = exo.get_instances()
    sections = {}
    for instance in instances:
        ip = instance["public-ip"]
        labels = instance["labels"] | {"name": instance["name"]}
        for key in ["context", "group", "name"]:
            if key not in labels:
                continue
            value = labels[key]
            if value not in sections:
                sections[value] = []
            sections[value].append(ip)
    for section in sorted(sections.keys()):
        ips = sections[section]
        file.write(f"[{section}]\n")
        for ip in ips:
            file.write(f"{ip}\n")
        file.write("\n")


@cli.command(help="Generate an Ansible Playbook for Group Users")
@click.option(
    "--group-file",
    type=click.File("r", encoding="utf-8"),
    help="groups file to be read",
)
@click.option(
    "--playbook",
    type=click.File("w", encoding="utf-8"),
    help="playbook file to be written",
)
def user_playbook(group_file, playbook):
    group = yaml.load(group_file.read(), Loader=yaml.SafeLoader)
    content = []
    for user in group["users"]:
        host_name = to_host_name(user["name"])
        user_name = default_user_name
        ssh_key = user["ssh-key"]
        play = {
            "name": f"User Setup for {user_name}",
            "hosts": host_name,
            "become": True,
            "tasks": [
                {
                    "name": "User Created",
                    "user": {
                        "name": user_name,
                        "shell": "/usr/bin/bash",
                        "create_home": True,
                        "home": f"/home/{user_name}",
                        "password": "*",
                        "append": True,
                        "groups": ["sudo"],
                    },
                },
                {
                    "name": "Key Authorized",
                    "authorized_key": {
                        "user": user_name,
                        "key": ssh_key,
                    },
                },
            ],
        }
        content.append(play)
    yaml.dump(content, playbook)


@cli.command(help="Generate Filtered HTML Overview Page for Instance Access Details")
@click.option("--key", help="filter by label key (e.g. context, group)")
@click.option("--value", help="filter by label value")
@click.option("--file", type=click.File("w", encoding="utf-8"), help="HTML output file")
@click.pass_context
def overview(ctx, key, value, file):
    exo = ctx.obj["exo"]
    instances = exo.get_instances()
    if key and value:
        instances = [i for i in instances if i["labels"].get(key, "") == value]
    if not instances:
        fatal(f"no instances matched label filter {key}={value}")
    output = []
    for instance in sorted(instances, key=lambda i: i["name"]):
        ip = instance["public-ip"]
        host_name = instance["name"]
        ssh_cmd = f"ssh {default_user_name}@{ip}"
        name_parts = host_name.split("-")
        first_name = name_parts[0].capitalize()
        last_name = name_parts[1].capitalize()
        swiss_name = f"{last_name}, {first_name}"
        output.append((swiss_name, host_name, ip, ssh_cmd))
    output = sorted(output, key=lambda o: o[0])
    env = Environment(loader=PackageLoader("achim"), autoescape=select_autoescape())
    template = env.get_template("overview.html")
    if key and value:
        condition = f"{key}={value}"
    else:
        condition = ""
    file.write(template.render(condition=condition, instances=output))


@cli.command(help="List Instance Types")
@click.option("--family", help="Instance Family", default="standard")
@click.pass_context
def list_instance_types(ctx, family):
    exo = ctx.obj["exo"]
    filter_rules = {
        "authorized": True,
        "family": family,
    }
    instance_types = exo.get_instance_types(filter_rules)
    for instance_type in instance_types:
        print(instance_type)


@cli.command(help="Create a Private Network")
@click.option("--name", help="Network Name", required=True)
@click.option("--description", help="Network Description")
@click.option("--start-ip", help="Start of IP Range", default="10.0.0.1")
@click.option("--end-ip", help="End of IP Range", default="10.0.0.150")
@click.option("--netmask", help="Subnet Mask", default="255.255.255.0")
@click.pass_context
def create_network(ctx, name, description, start_ip, end_ip, netmask):
    must_be_valid_name(name)
    must_be_valid_ipv4(start_ip)
    must_be_valid_ipv4(end_ip)
    must_be_valid_ipv4(netmask)
    exo = ctx.obj["exo"]
    result = exo.create_network(name, start_ip, end_ip, netmask, description)
    print(result)


@cli.command(help="List Private Networks")
@click.option("--contains", help="filter network name (case insentitive)", default="")
@click.pass_context
def list_networks(ctx, contains):
    networks = get_networks(ctx, contains)
    for network in networks:
        print(network)


@cli.command(help="Attach a Private Network to an Instance")
@click.option("--network", help="Name of the Network", required=True)
@click.option("--instance", help="Name of the Instance", required=True)
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


@cli.command(help="Check Instance State for a Label/Value Combination")
@click.option("--label", help="Label to be matched.")
@click.option("--value", help="Value to be matched.")
@click.pass_context
def state(ctx, label, value):
    exo = ctx.obj["exo"]
    instances = exo.get_instance_by(label, value)
    instances = [(i["labels"].get("owner", ""), i["state"]) for i in instances]
    for owner, state in sorted(instances, key=lambda i: (i[1], i[0])):
        print(f"{owner:40s} {state}")


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
