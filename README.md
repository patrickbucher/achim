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

TODO: implement and document

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
    - [ ] create instances from groups file
    - [ ] stop ...
    - [ ] start ...
    - [ ] destroy ...
- groups files
    - [ ] assign tags to user to be used as labels