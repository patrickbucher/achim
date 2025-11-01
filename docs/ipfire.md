# IPFire

## Scenario

- Hosts
    - Windows
    - Ubuntu
    - Firewall
- Networks
    - green: 255.255.0.0/16
        - firewall: 192.168.0.1
        - windows: 192.168.0.10
    - orange: 255.255.255.0/24
        - firewall: 10.0.0.1
        - ubuntu: 10.0.0.10

## Problem

Interfaces are assigned randomly, so scenario networks and pre-configured networks do not match.

## Solution

First, figure out current IP configuration in _Address settings_, for example:

- this is just some random pre-configuration
    - green: 10.0.0.1 (wrong, this is the orange network!)
    - orange: 10.0.1.1 (wrong, this is the wrong IP)
    - red: DHCP (ok)

In this example, the cards have been assigned the wrong way.

This assignment can be changed in _Drivers and card assignments_.

- starting configuration:
    - green: 3
    - red: 2
    - orange: 4
- requird configuration:
    - green: change to 4
    - red: leave at 2
    - orange: change to 3

First, **write down the MAC addresses of those interfaces**!

- Green: 3 (0a:5d:b6:37:e9:29)
- Red: 2 (06:66:fa:00:0c:1f)
- Orange: 4 (0a:69:78:37:e9:2b)

Second, remove the green and orange interface.

Third, re-assign them, switching the Green and Orange card.

### Check

From the Windows VM, access IPFire through [https://192.168.0.1:444/](https://192.168.0.1:444/)