from os import PathLike
from os.path import join
from flask import Flask, request
from typing import Any, Callable    
from exceptions import *
from time import time
from math import floor
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