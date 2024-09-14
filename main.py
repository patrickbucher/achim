#!/usr/bin/env python3

import os
import sys

from dotenv import load_dotenv
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


if __name__ == '__main__':
    load_dotenv()
    username = os.getenv('CLOUD_USERNAME')
    api_key = os.getenv('CLOUD_API_KEY')
    if not username or not api_key:
        print('must provide CLOUD_USERNAME and CLOUD_API_KEY', file=sys.stderr)
        sys.exit(1)

    cls = get_driver(Provider.EXOSCALE)
    driver = cls(username, api_key)
    print(driver)
