# acapy-minimal-example

Create a minimal reproducible example.

## Goals for this Project

- Minimal Setup (everything runs in containers)
- Quickly reproduce an issue or demonstrate a feature by writing one simple
  script or pytest tests.
- Generator for common agent setups (`Dockerfile`s + `docker-compose.yml`). For example:
    - Alice, Bob
    - Alice, Bob, Mediator
    - Issuer, Holder, Verifier
    - Endorser, Issuer, Holder, Verifier
    - ACA-Py, Echo (Remote controlled static agent; for sending raw messages)
    - Any combination of the above with a specified set of plugins installed.
    - Any combination of the above with tails server and/or tunnel
    - etc.

We're still working on achieving these goals, particularly the generator.

Contributions are welcome.

## Controller

Included in this repo is a simple "hackable" controller. The controller provides
an interface for interacting with an ACA-Py instance. The primary operations
are:

- `get` - perform a get request to the agent
- `post` - perform a post request to the agent
- `record`, `record_with_values`, `event_queue` - await and retrieve
  records/events emitted by the agent

The controller is inspired by a number of similar efforts, including the
auto-generated client libraries
[acapy-client](https://github.com/Indicio-tech/acapy-client) and
[aries-cloudcontroller](https://github.com/Indicio-tech/acapy-client), the
[acapy-revocation-demo](https://github.com/didx-xyz/aries-cloudcontroller-python)
(which is often used internally at Indicio exactly the way we intend this repo
to be used), and the [integration test controllers in ACA-Py's BDD
tests](https://github.com/Indicio-tech/acapy-revocation-demo/).

This controller differs from these in a few key ways:

- This controller is intended to be as simple and hackable as possible. Specific
  operations like creating an out-of-band connection or issuing a credential are
  not implemented directly on the controller. Instead, the building blocks for
  these operations are made available so the library consumer can tweak
  parameters and request bodies directly. This allows the consumer to have the
  flexibility to hit edge cases or demonstrate changes without needing to
  implement a new request method or generate a new client.
- Models for request bodies are included but optional. This helps strike a
  balance between flexibility and ease of use that isn't achieved in an
  interface like the one provided by the acapy-revocation-demo controller, for
  instance. In addition to the included models, a dictionary, pydantic model,
  dataclass (from python's standard `dataclasses`), or a class/instance
  implementing a `serialize` and `deserialize` method can be used as the request
  body.
- Deserialization (and typing) of response bodies is built into all operations.
  This makes it far more convenient to validate and access the data of an ACA-Py
  response. This is done by passing the desired response type to the operation.
  Supported types match the supported auto-serialzation types for request
  bodies: the included models, pydantic models, dataclasses, and classes
  implementing `serialize` and `deserialize`.
- This controller provides a system for capturing webhooks/events that is well
  suited for a testing or demonstration scenario.


## Examples

A number of examples can be found in the [examples](./examples) directory. Each
of these contains a `docker-compose.yml` and a `example.py`. You can run each
example by `cd`ing into the directory and running:

```sh
$ cd examples/example_to_try_out
$ docker-compose run example
$ docker-compose down -v
```

## Instructions on Running Tests

To run the tests:

```
docker-compose run tests
```

This should build everything as needed. If not:

```
docker-compose build
```

To stop and remove all running containers:

```
docker-compose down
```

> Note: You shouldn't have to run `docker-compose down` between tests the way
> things are currently set up but doing so should give the cleanest state
> possible for inspection after the tests complete

### Custom ACA-Py Images/Versions

Presently, ACA-Py version 0.7.4 is used. This can be changed by modifying the
build parameter of the ACA-Py services. A commented out example is included. You
can adjust `acapy_url` as needed. If you _do_ change the `acapy_url`, you need
to make sure you manually trigger a build with `docker-compose build`.

#### Instructions on Running with a Local Image

One can also build the docker images from a local ACA-Py repo contents, if so desired. 

From the root of the ACA-Py repo, do:

```
docker build -t acapy-test-image -f docker/Dockerfile.run .
```

Then remove the build mapping from the ACA-Py services (back in [the
acapy-minimal-example](https://github.com/Indicio-tech/acapy-minimal-example)
repo) and replace it with `image: acapy-test-image`

