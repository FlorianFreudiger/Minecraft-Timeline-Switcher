from __future__ import annotations

import os

import requests
import logging
from typing import Any

from models import UpdateTarget, Variant


class Portainer(UpdateTarget):
    hostname: str
    stack_name: str
    headers: dict[str, str]
    template_path: str

    @staticmethod
    def from_config(config: dict[str, Any]) -> Portainer:
        host = config["portainer"]["hostname"]
        stack = config["portainer"]["stack_name"]

        headers = {}
        for header in config["portainer"]["header"]:
            headers[header["name"]] = header["value"]

        template_path = os.path.join("../config", config["portainer"]["template"])
        if not os.path.isfile(template_path):
            raise FileNotFoundError(f"Portainer template file not found at {template_path}")

        return Portainer(host, stack, headers, template_path)

    def __init__(self, hostname: str, stack_name: str, headers: dict[str, str], template_path: str) -> None:
        self.hostname = hostname
        self.stack_name = stack_name
        self.headers = headers
        self.template_path = template_path

    def get_request(self, endpoint: str):
        url = f"https://{self.hostname}/api/{endpoint}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def put_request(self, endpoint: str, body: dict, params: dict = None):
        url = f"https://{self.hostname}/api/{endpoint}"
        response = requests.put(url, headers=self.headers, json=body, params=params)
        response.raise_for_status()
        return response.json()

    def update_variant(self, variant: Variant) -> None:
        compose = variant.generate_compose(self.template_path)
        logging.info(f"Updating Portainer stack {self.stack_name}")

        # Get stack id
        stacks = self.get_request("stacks")

        stack_id = None
        endpoint_id = None
        previous_env = None
        for stack in stacks:
            if stack["Name"] == self.stack_name:
                stack_id = stack["Id"]
                endpoint_id = stack["EndpointId"]
                previous_env = stack["Env"]
                break

        if stack_id is None:
            raise RuntimeError(f"Stack {self.stack_name} not found.")

        # Update stack
        update_body = {
            "env": previous_env,
            "prune": True,
            "pullImage": True,
            "stackFileContent": compose,
        }
        self.put_request(f"stacks/{stack_id}", update_body, params={"endpointId": endpoint_id})
