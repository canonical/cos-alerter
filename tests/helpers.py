# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

DESTINATIONS = [
    "mailtos://user:pass@domain/?to=example-0@example.com,example-1@example.com",
    "slack://xoxb-1234-1234-4ddbc191d40ee098cbaae6f3523ada2d/#general",
    "pagerduty://integration-key@api-key",
]

CONFIG = {
    "watch": {
        "down_interval": "5m",
        "wait_for_first_connection": False,
        "clients": {
            "clientid1": {
                "key": "822295b207a0b73dd4690b60a03c55599346d44aef3da4cf28c3296eadb98b2647ae18863cc3ae8ae5574191b60360858982fd8a8d176c0edf646ce6eee24ef9",
                "name": "Instance Name 1",
            },
        },
    },
    "notify": {
        "destinations": DESTINATIONS,
        "repeat_interval": "1h",
    },
}
