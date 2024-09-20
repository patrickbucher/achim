#!/usr/bin/env python3

import sys

from dotenv import dotenv_values

from exoscale import Exoscale

templates = {"debian12": "Linux Debian 12 (Bookworm) 64-bit"}

instance_type_filter = {
    "authorized": True,
    "family": "standard",
    "cpus": 1,
}

if __name__ == "__main__":
    config = dotenv_values(".env")
    keys = [
        "EXOSCALE_API_KEY",
        "EXOSCALE_API_SECRET",
        "EXOSCALE_ZONE",
    ]
    if any(filter(lambda k: k not in config, keys)):
        print("missing settings in .env file (see sample.env)", file=sys.stderr)
        sys.exit(1)

    exo = Exoscale(config)

    template = exo.get_template_by_name(templates["debian12"])
    instance_types = exo.get_instance_types(instance_type_filter)
    smallest = sorted(instance_types, key=lambda it: it["memory"])[0]
    ssh_key = exo.get_ssh_key("patrick.bucher")
    labels = {
        "context": "m346", # static
        "group": "inf23a", # TODO: from command-line argument
        "purpose": "ssh-exercise", # TODO: from groups file (with fallback)
        "owner": "patrick_bucher", # TODO: from groups file
    }

    instance = exo.create_instance("xanadu", template, smallest, ssh_key, labels)
    print(instance)
