#!/usr/bin/env python3

import sys

import click
from dotenv import dotenv_values
from exoscale import Exoscale
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
    instance = exo.create_instance(name, template, smallest, ssh_key, labels)
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
        for key in ["context", "group", "purpose"]:
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


if __name__ == "__main__":
    cli()
