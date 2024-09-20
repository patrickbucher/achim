# achim: Advanced Cloud Hyperscaling Infrastructure Manager

## Usage

Get help:

    $ python achim.py --help

Get help on a command (e.g. `create-instance`):

    $ python achim.py create-instance --help

Create an instance:

    $ python achim.py create-instance --name demo --keyname patrick.bucher

## TODO

- inventory
    - [ ] generate inventory by labels
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