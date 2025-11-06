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
