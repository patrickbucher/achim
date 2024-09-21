# achim: Advanced Cloud Hyperscaling Infrastructure Manager

Prototype for Exoscale Compute Instances

## Usage

Get help:

    $ python achim.py --help

Get help on a command (e.g. `create-instance`):

    $ python achim.py create-instance --help

### Instances

Create an instance:

    $ python achim.py create-instance --name demo --keyname patrick.bucher

Start an instance:

    $ python achim.py start-instance --name demo

Stop an instance:

    $ python achim.py stop-instance --name demo

Destroy an instance:

    $ python achim.py destroy-instance --name demo --sure

### Groups

Create instances for a group (as defined in `group.yaml`):

    $ python achim.py create-group --file group.yaml --context m346 --keyname patrick.bucher

Start instances for a group:

    $ python achim.py start-group --name students

Stop instances for a group:

    $ python achim.py stop-group --name students

Destroy instances for a group:

    $ python achim.py stop-group --name students --sure

### Inventory

Create an Ansible inventory of existing instances, grouped by labels `context`,
`group`, and `purpose`:

    $ python achim.py inventory --file inventory.ini

### Playbook

Create an Ansible playbook to create a user for its instance with its SSH key authorized:

    $ python achim.py user-playbook --group-file group.yaml --playbook students.yaml

## TODO

- inventory/playbooks
    - [x] generate inventory by labels
    - [x] add one section per owner to inventory
    - [x] generate users playbook from group file
- single
    - [x] create an instance
    - [x] stop an instance
    - [x] start an instance
    - [x] destroy an instance
- multiple
    - [x] create instances from groups file
    - [x] stop instances from groups file
    - [x] start instances from groups file
    - [x] destroy instances from groups file
- reporting
    - [ ] create textual output for group (SSH command)
        - e.g. `ssh patrick.bucher@85.12.128.99`
        - ordered by _last_ name!
- groups files
    - [ ] assign tags to user to be used as labels