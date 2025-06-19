#!/usr/bin/env python

import logging
from time import sleep

from confluent_kafka.admin import AdminClient


def wait_for_topics(bootstrap_servers: str, *topics: str) -> None:
    client: AdminClient = AdminClient({"bootstrap.servers": bootstrap_servers})
    while True:
        existing_topics = client.list_topics().topics.keys()
        if all(t in existing_topics for t in topics):
            logging.info(f"Found topics {topics}")
            return
        else:
            logging.info(f"Waiting for topics {topics}")
            sleep(1.0)
