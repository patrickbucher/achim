# achim: Advanced Cloud Hyperscaling Infrastructure Manager

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

## TODO

- inventory
    - [x] generate inventory by labels
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
- groups files
    - [ ] assign tags to user to be used as labels