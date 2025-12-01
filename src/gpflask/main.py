from os import PathLike
from os.path import join, exists
from flask import Flask, request
from typing import Any, Callable    
from .exceptions import *
from time import time
from math import floor
import json
import traceback

class DataPacket:
    def __init__(self, source: str, timestamp: int, data: dict[str, Any]):
        self.source = source
        self.timestamp = timestamp
        self.data = data
    
    def get_data(self, path: str | list[str]) -> Any | None:
        if type(path) == str:
            return self.data[path]
        elif type(path) == list:
            d = self.data
            for p in path:
                try:
                    d = d[p]
                except IndexError:
                    return None
            return d
        return None

class GPFlask(Flask):
    def __init__(self, import_name: str, static_url_path: str | None = None, static_folder: str | PathLike[str] | None = "static", static_host: str | None = None, host_matching: bool = False, subdomain_matching: bool = False, template_folder: str | PathLike[str] | None = "templates", instance_path: str | None = None, instance_relative_config: bool = False, root_path: str | None = None):
        super().__init__(import_name, static_url_path, static_folder, static_host, host_matching, subdomain_matching, template_folder, instance_path, instance_relative_config, root_path)
        self.storage: list[DataPacket] = []
        self.named_storage: dict[str, dict[str, Any]] = {}

    def get_request_host(self) -> str:
        req_host = None
        try:
            req_host = join(request.host_url, request.path)
            return req_host
        except RuntimeError as e:
            raise ServerStoreException(traceback.format_exc())

    def store_packet(self, data: dict[str, Any]) -> int:
        self.storage.append(DataPacket(self.get_request_host(), floor(time()), data))
        return len(self.storage) - 1
    
    def store_named_packet(self, name: str, data: dict[str, Any]) -> None:
        self.named_storage.update({name: data})

    def store_named_packet_safe(self, name: str, data: dict[str, Any]) -> None:
        if self.named_storage[name]: return
        self.named_storage.update({name: data})
    
    def get_named_packet(self, name: str) -> dict[str, Any]:
        return self.named_storage[name]

    def get_packets_with_condition(self, fn: Callable[[DataPacket], bool]) -> list[DataPacket]:
        return list(filter(fn, self.storage))
    
    def get_packets_from_host(self, host: str) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: x.source == host)
    
    def get_packets_before_time(self, timestamp: int) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: x.timestamp < timestamp)
    
    def get_packets_after_time(self, timestamp: int) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: x.timestamp > timestamp)
    
    def get_packets_during_time(self, timestamp: int) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: x.timestamp == timestamp)

    def get_packets_before_during_time(self, timestamp: int) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: x.timestamp <= timestamp)
    
    def get_packets_after_during_time(self, timestamp: int) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: x.timestamp >= timestamp)
    
    def get_packets_between_time(self, begin_timestamp: int, end_timestamp: int) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: begin_timestamp < x.timestamp < end_timestamp)
    
    def get_packets_between_during_time(self, begin_timestamp: int, end_timestamp: int) -> list[DataPacket]:
        return self.get_packets_with_condition(lambda x: begin_timestamp <= x.timestamp <= end_timestamp)
    
    def save_as_formatted_log(self, output_path: str) -> float:
        s = time()
        out = join(output_path, f"{floor(s)}.log")
        if exists(out):
            raise FileExistsError("A log has already been created at this timestamp. Are you saving your logs in a loop?")
        
        data = "Named Storage:\n"
        for v in self.named_storage:
            data += f"{v}: {self.named_storage[v]}\n"

        data += "\nUnnamed Storage:\n"
        for v in self.storage:
            data += f"Source: {v.source}\nTimestamp: {v.timestamp}\nData: {v.data}\n"

        with open(out, "wt") as f:
            f.write(data)

        return time() - s

    def save_as_formatted_log_append(self, output_path: str) -> float:
        s = time()
        out = join(output_path, f"{floor(s)}.log")
        if exists(out):
            raise FileExistsError("A log has already been created at this timestamp. Are you saving your logs in a loop?")
        
        with open(out, "at") as f:
            f.write("Named Storage:\n")
        for v in self.named_storage:
            with open(out, "at") as f:
                data = f"{v}: {self.named_storage[v]}\n"
                f.write(data)
        with open(out, "at") as f:
            f.write("\nUnnamed Storage:\n")
        for v in self.storage:
            with open(out, "at") as f:
                data = f"Source: {v.source}\nTimestamp: {v.timestamp}\nData: {v.data}\n"
                f.write(data)
        
        return time() - s
    
    def get_as_json(self) -> dict[str, list[DataPacket] | dict[str, dict[str, Any]]]:
        return {"named_storage": self.named_storage, "unnamed_storage": self.storage}

    def save_as_json(self, output_path: str) -> float:
        s = time()
        out = join(output_path, f"{floor(s)}.json")
        if exists(out):
            raise FileExistsError("A JSON file has already been created at this timestamp. Are you saving the file in a loop?")
        
        data = {"named_storage": self.named_storage, "unnamed_storage": self.storage}
        with open(out, "wt") as f:
            f.write(json.dumps(data))

        return time() - s
    
    def load_from_json(self, input_path: str) -> float:
        s = time()
        if not exists(input_path):
            raise FileNotFoundError("The JSON file doesn't exist")
        
        with open(input_path, "rt") as f:
            try:
                data = json.loads(f.read())
                if (not data["named_storage"]) or (not data["unnamed_storage"]):
                    raise LoadStorageException("The JSON file is missing 1 or more of the following items in the root object: \"named_storage\", \"unnamed_storage\"")
                self.storage = data["unnamed_storage"]
                self.named_storage = data["named_storage"]
            except json.JSONDecodeError:
                raise LoadStorageException("The JSON file contained invalid syntax. See traceback for more details.")

        return time() - s