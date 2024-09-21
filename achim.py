#!/usr/bin/env python3

import sys

import click
from dotenv import dotenv_values
from exoscale import Exoscale
from jinja2 import Template
import yaml

templates = {"debian12": "Linux Debian 12 (Bookworm) 64-bit"}

instance_type_filter = {
    "authorized": True,
    "family": "standard",
    "cpus": 1,
}


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
        print("missing settings in .env file (see sample.env)", file=sys.stderr)
        sys.exit(1)

    ctx.ensure_object(dict)
    ctx.obj["exo"] = Exoscale(config)


@cli.command(help="Create a Compute Instance")
@click.option("--name", required=True, help="instance name (hostname)")
@click.option("--keyname", required=True, help="name of registered SSH key")
@click.option("--context", help="context (label)", default="default")
@click.option("--group", help="group (label)", default="default")
@click.option("--purpose", help="purpose (label)", default="default")
@click.option("--owner", help="owner (label)", default="default")
@click.pass_context
def create_instance(ctx, name, keyname, context, group, purpose, owner):
    exo = ctx.obj["exo"]
    existing = exo.get_instances()
    if any([instance["name"] == name for instance in existing]):
        print(f"name '{name}' is already in use", file=sys.stderr)
        sys.exit(1)
    instance = do_create_instance(exo, name, keyname, context, group, purpose, owner)
    print(instance)


def do_create_instance(exo, name, keyname, context="", group="", purpose="", owner=""):
    template = exo.get_template_by_name(templates["debian12"])
    instance_types = exo.get_instance_types(instance_type_filter)
    smallest = sorted(instance_types, key=lambda it: it["memory"])[0]
    ssh_key = exo.get_ssh_key(keyname)
    labels = {
        "context": context,
        "group": group,
        "purpose": purpose,
        "owner": owner,
    }
    labels = {k: v for (k, v) in labels.items() if v}
    return exo.create_instance(name, template, smallest, ssh_key, labels)


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
@click.pass_context
def create_group(ctx, file, keyname, context):
    exo = ctx.obj["exo"]
    existing = exo.get_instances()
    group = yaml.load(file.read(), Loader=yaml.SafeLoader)
    group_name = group["name"]
    users = group["users"]
    user_names = {u["name"] for u in users}
    existing_names = {e["name"] for e in existing}
    already_used = user_names.intersection(existing_names)
    if already_used:
        print(f"names '{already_used}' are already in use", file=sys.stderr)
        sys.exit(1)
    instances = []
    for user in users:
        name = user["name"].replace("_", ".")
        purpose = user.get("purpose", "")
        instance = do_create_instance(
            exo, name, keyname, context, group_name, purpose, name
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
        labels = instance["labels"]
        for key in ["context", "group", "purpose", "owner"]:
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
        user_name = user["name"].replace("_", ".")
        ssh_key = user["ssh-key"]
        play = {
            "name": f"User Setup for {user_name}",
            "hosts": user_name,
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


@cli.command(help="Generate  Filtered HTML Overview Page for Instance Access Details")
@click.option("--key", help="filter by label key (e.g. context, group)")
@click.option("--value", help="filter by label value")
@click.option("--file", type=click.File("w", encoding="utf-8"), help="HTML output file")
@click.pass_context
def overview(ctx, key, value, file):
    exo = ctx.obj["exo"]
    instances = exo.get_instances()
    instances = [i for i in instances if i["labels"].get(key, "") == value]
    if not instances:
        print(f"no instances matched label filter {key}={value}", file=sys.stderr)
        sys.exit(1)
    output = []
    for instance in sorted(instances, key=lambda i: i["name"]):
        ip = instance["public-ip"]
        name = instance["name"]
        ssh_cmd = f"ssh {name}@{ip}"
        output.append((name, ip, ssh_cmd))
    with open("./templates/overview.html") as f:
        template = Template(f.read())
        file.write(template.render(key=key, value=value, instances=output))


if __name__ == "__main__":
    cli()
