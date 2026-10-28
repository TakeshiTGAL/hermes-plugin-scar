"""Only loopback is local. A LAN address is not."""

from support import local_host


def test_loopback_names_are_local():
    assert local_host.host_is_local("127.0.0.1")
    assert local_host.host_is_local("127.0.0.2")
    assert local_host.host_is_local("::1")
    assert local_host.host_is_local("[::1]")
    assert local_host.host_is_local("localhost")
    assert local_host.host_is_local("LOCALHOST")
    assert local_host.host_is_local("localhost.")


def test_lan_and_other_ranges_are_not_local():
    refused = [
        "10.0.0.1",
        "192.168.1.50",
        "172.16.0.1",
        "0.0.0.0",
        "169.254.169.254",
        "::",
        "fe80::1",
        "224.0.0.1",
        "240.0.0.1",
        "192.0.2.1",
        "example.com",
        "",
        "127.0.0.1 ",
        "user@127.0.0.1",
        "::1%eth0",
        None,
    ]
    for host in refused:
        assert local_host.host_is_local(host) is False
