from __future__ import annotations

import requests
from typing import Any


class Portainer:
    hostname: str
    stack_name: str
    headers: dict[str, str]

    @staticmethod
    def from_config(config: dict[str, Any], secrets: dict[str, Any]) -> Portainer:
        host = config["portainer"]["hostname"]
        stack = config["portainer"]["stack_name"]

        headers = {}
        for header in secrets["portainer"]["header"]:
            headers[header["name"]] = header["value"]

        return Portainer(host, stack, headers)

    def __init__(self, hostname: str, stack_name: str, headers: dict[str, str]) -> None:
        self.hostname = hostname
        self.stack_name = stack_name
        self.headers = headers

    def get_request(self, endpoint: str):
        url = f"https://{self.hostname}/api/{endpoint}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error getting {endpoint}: {response.status_code} {response.text}")
            exit(1)
        else:
            return response.json()

    def put_request(self, endpoint: str, body: dict, params: dict = None):
        url = f"https://{self.hostname}/api/{endpoint}"
        response = requests.put(url, headers=self.headers, json=body, params=params)
        if response.status_code != 200:
            print(f"Error putting {endpoint}: {response.status_code} {response.text}")
            exit(1)
        else:
            return response.json()

    def update_stack(self, compose: str) -> None:
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
            print(f"Stack {self.stack_name} not found.")
            exit(1)

        # Update stack
        update_body = {
            "env": previous_env,
            "prune": True,
            "pullImage": True,
            "stackFileContent": compose,
        }
        self.put_request(f"stacks/{stack_id}", update_body, params={"endpointId": endpoint_id})
