# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

DESTINATIONS = [
    "mailtos://user:pass@domain/?to=example-0@example.com,example-1@example.com",
    "slack://xoxb-1234-1234-4ddbc191d40ee098cbaae6f3523ada2d/#general",
]

CONFIG = {
    "watch": {
        "down_interval": "5m",
        "wait_for_first_connection": False,
        "clients": {
            "clientid1": {
                "key": "clientkey1",
                "name": "Instance Name 1",
            },
        },
    },
    "notify": {
        "destinations": DESTINATIONS,
        "repeat_interval": "1h",
    },
}
