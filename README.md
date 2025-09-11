# achim: Advanced Cloud Hyperscaling Infrastructure Manager

Prototype for Exoscale Compute Instances

![I'll start my own cloud infrastructure. With achim and Ansible!](bender.jpg)

## Setup

Create a virtual Python environment:

    $ python -m venv env

Activate it (Linux/Bash):

    $ . env/bin/activate

Install `achim` in editable mode:

    $ pip install -e .

Create a `.env` file:

    $ cp sample.env .env

Fill in all the data in `.env`:

    EXOSCALE_API_KEY=EXO****
    EXOSCALE_API_SECRET=****
    EXOSCALE_ZONE=ch-gva-2

## Usage

Get help:

    $ achim --help

Get help on a command (e.g. `create-instance`):

    $ achim create-instance --help

### Instances

Create an instance:

    $ achim create-instance --name demo --keyname patrick.bucher

Start an instance:

    $ achim start-instance --name demo

Stop an instance:

    $ achim stop-instance --name demo

Destroy an instance:

    $ achim destroy-instance --name demo --sure

### Groups

Create instances for a group (as defined in `group.yaml`):

    $ achim create-group --file group.yaml --context m346 --keyname patrick.bucher

Start instances for a group:

    $ achim start-group --name students

Stop instances for a group:

    $ achim stop-group --name students

Destroy instances for a group:

    $ achim stop-group --name students --sure

### Scenarios

Create a new scenario (as defined in `scenario.yaml`) for a group (as defined in `group.yaml`):

    $ achim create-scenario --scenario scenario.yaml --group group.yaml --keyname t15 --context m987 --autostart    

Destroy it again (using the `name` defined in `scenario.yaml`):

    $ achim destroy-scenario --name 'Modul 987 Lab Exercise'

### Inventory

Create an Ansible inventory of existing instances, grouped by labels `context`,
`group`, and `purpose`:

    $ achim inventory --file inventory.ini

### Playbook

Create an Ansible playbook to create a user for its instance with its SSH key authorized:

    $ achim user-playbook --group-file group.yaml --playbook students.yaml

### Overview

Create an HTML overview page for names, IPs, and `ssh` commands:

    $ achim overview --key group --value students --file overview.html