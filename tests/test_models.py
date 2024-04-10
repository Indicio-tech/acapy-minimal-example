from typing import Tuple
from acapy_controller.controller import Minimized


def test_import():
    from acapy_controller.models import ConnRecord

    assert ConnRecord


def test_into(did_exchange: Tuple[Minimized, Minimized]):
    from acapy_controller.models import ConnRecord

    alice, bob = did_exchange
    alice_conn = alice.into(ConnRecord)
    bob_conn = bob.into(ConnRecord)
    assert bob_conn.connection_protocol
    assert alice_conn.invitation_mode
