# acapy-minimal-example

Create a minimal reproducible example.

## Quick Start

If you'd like to create a minimal reproducible example, consider starting from the template repository: [acapy-minimal-example-template](https://github.com/Indicio-tech/acapy-minimal-example-template)

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

- HTTP Request methods: `get`, `post`, `put`, `delete`
- `event`, `event_with_values`, `event_queue` - await and retrieve
  events emitted by the agent

The controller is inspired by a number of similar efforts, including the
auto-generated client libraries
[acapy-client](https://github.com/Indicio-tech/acapy-client) and
[aries-cloudcontroller](https://github.com/didx-xyz/aries-cloudcontroller-python), the
[acapy-revocation-demo](https://github.com/Indicio-tech/acapy-revocation-demo/)
(which is often used internally at Indicio exactly the way we intend this repo
to be used), and the [integration test controllers in ACA-Py's BDD
tests](https://github.com/hyperledger/aries-cloudagent-python/tree/main/demo/runners).

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
  instance. In addition to the included models, a dictionary,
  dataclass (from python's standard `dataclasses`), or a class/instance
  implementing a `serialize` and `deserialize` method can be used as the request
  body.
- Deserialization (and typing) of response bodies is built into all operations.
  This makes it far more convenient to validate and access the data of an ACA-Py
  response. This is done by passing the desired response type to the operation.
  Supported types match the supported auto-serialzation types for request
  bodies: the included models, dataclasses, and classes
  implementing `serialize` and `deserialize`.
- This controller provides a system for capturing webhooks/events that is well
  suited for a testing or demonstration scenario.


## Protocols

Several helper methods are included in [protocols.py](./acapy_controller/protocols) that are useful for causing two ACA-Py instances to engage in a protocol. The `Controller` instances connected to the ACA-Py instances are used to orchestrate each of the Admin API calls required and await the expected webhooks to see the given protocol through to completion.

Some of the implemented protocols include:

- DID Exchange (`didexchange`) - Connect two ACA-Py instances using OOB + DID Exchange and return the connection records from each instance.
- Issue Credential v2: Indy (`indy_issue_credential_v2`) - Conduct a credential issuance of an AnonCreds credential with one ACA-Py instance acting as the issuer and the other as the holder.
- Present Proof v2: Indy (`indy_present_proof_v2`) - Conduct a presentation request of an AnonCreds credential with one ACA-Py instance acting as the verifier and the other as the prover.
- Issue Credential v2: json-ld (`jsonld_issue_credential`) - Conduct a credential issuance of an LDP-VC credential with one ACA-Py instance acting as the issuer and the other as the holder.
- Present Proof v2: json-ld (`jsonld_present_proof`) - Conduct a presentation request of an LDP-VC credential with one ACA-Py instance acting as the verifier and the other as the prover.

In addition to protocol helpers, some other common admin operations have some automated helpers:

- Indy Onboarding (`indy_anoncred_onboard`) - Auto-accept the TAA of the Indy network, create a DID, and anchor it to the network. The helper will attempt to automatically detect the connected network and determine the URL of the "self-serve" endpoint for publishing an Endorser DID. All VON Network instances (that exposes a `register` endpoint) and Indicio Test/Demo Networks are supported.
> [!WARNING]
> By using this tool, you are expressing your acceptance of the Transaction Author Agreement of the network to which you are connecting.
- Indy AnonCred credential artifact creation (`indy_anoncred_credential_artifacts`) - Creates a schema and credential definition for that schema. Supports setting revocation on the resulting cred def.


## Models

This project includes Pydantic Models auto-generated from ACA-Py's OpenAPI specification. These models provide a way to more easily access the information returned from ACA-Py's Admin API or to add type safety to the requests being made to the Admin API. To use these models, the `models` extra must be installed, e.g.:

```sh
pip install acapy-controller[models]
```

The models can be useful on their own. It is particularly useful to use them for the `response` parameter of an Admin API request or as the `event_type` parameter when awaiting an event:

```python
from acapy_controller import Controller
from acapy_controller.models import ConnectionList, ConnRecord

async def main():
    async with Controller(base_url="http://acapy.example.com/admin") as agent:
        conns = await agent.get(
            "/connections",
            response=ConnectionList
        )
        assert conns.results

        # ...

        conn = await agent.event_with_values(
            topic="connections",
            state="active",
            event_type=ConnRecord
        )
        assert conn.connection_id
```

This strategy is quite effective; however, it is common to use this library with an as of yet unreleased version of ACA-Py where an updated OpenAPI specification is not yet available. Because of this, usage of these models is purely optional to enable greater flexibility. If `response` or `event_type` are omitted from the above example, `conns` and `conn` will be simple dictionaries.

Because of the need to work with various ACA-Py versions, released and unreleased, the protocol helpers depend on a different set of models that minimize the amount of validation to the bare minimum required to complete the exchange. This should help keep the protocol helpers functioning across ACA-Py versions except when a more significant breaking change occurs.

## Events

The Controller can be used as a simple HTTP client to make Admin API requests to ACA-Py. For more interesting exchanges, though, ACA-Py depends on reporting events asynchronously to its controller, usually via posted webhooks. ACA-Py also supports delivering these events to connected WebSockets. Using a WebSocket and an ["Asynchronous Selective Queue"](https://github.com/dbluhm/async-selective-queue), the Controller also exposes a versatile interface for expecting and handling these webhook events.

See the example above under "Models" or [protocols.py](./acapy_controller/protocols.py) for how this can be used.

## Examples

A number of examples can be found in the [examples](./examples) directory. Each
of these contains a `docker-compose.yml` and a `example.py`. You can run each
example by `cd`ing into the directory and running:

```sh
cd examples/simple
docker-compose run example
# Clean up
docker-compose down -v
```

## Instructions on Running Tests

There are some automated tests used to validate the builtin protocol helpers.

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

## Testing the Examples

Pytest has been configured to run checks on the [examples](./examples). You can
run these with:

```
poetry run pytest -m examples
```

This will run the `example` service of each docker-compose file in each
directory inside of the `examples` folder.

### Custom ACA-Py Images/Versions

Presently, a specific version ACA-Py is used, using the images published to the
ACA-Py repository. This can be changed by modifying the build parameter of the
ACA-Py services. A commented out example is included. You can adjust
`acapy_url` as needed. If you _do_ change the `acapy_url`, you need to make
sure you manually trigger a build with `docker-compose build`.

#### Instructions on Running with a Local Image

One can also build the docker images from a local ACA-Py repo contents, if so desired. 

From the root of the ACA-Py repo, do:

```
docker build -t acapy-test -f docker/Dockerfile.run .
```

Then remove the build mapping from the ACA-Py services (back in [the
acapy-minimal-example](https://github.com/Indicio-tech/acapy-minimal-example)
repo) and replace it with `image: acapy-test`

