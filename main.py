#!/usr/bin/env python3

import sys

from dotenv import dotenv_values

from exoscale import Exoscale

supported_sizes = []

templates = {"debian12": "Linux Debian 12 (Bookworm) 64-bit"}

supported_locations = []

if __name__ == "__main__":
    config = dotenv_values(".env")
    keys = [
        "EXOSCALE_API_KEY",
        "EXOSCALE_API_SECRET",
        "EXOSCALE_ENVIRONMENT",
        "EXOSCALE_ZONE",
    ]
    if any(filter(lambda k: k not in config, keys)):
        print("missing settings in .env file (see sample.env)", file=sys.stderr)
        sys.exit(1)

    exo = Exoscale(config)
    template = exo.get_template_by_name(templates["debian12"])
    print(template)
