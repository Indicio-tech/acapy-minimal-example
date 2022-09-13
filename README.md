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
- This controller provides a system for capturing webhooks/events that is well
  suited for a testing or demonstration scenario.
