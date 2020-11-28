import logging
from collections import defaultdict
from typing import List, Dict, TypeVar, Any, Type

import simpy

from ether.core import Node
from ether.topology import Topology


class Message:
    source: Node
    destination: Node
    timestamp: int
    latency: float

    def __repr__(self):
        return f'{type(self).__name__}({self.__dict__})'


MessageT = TypeVar('MessageT', bound=Message)


class Ping(Message):
    pass


class Pong(Message):
    pass


class FindClosestBrokersRequest(Message):
    pass


class FindClosestBrokersResponse(Message):
    brokers: List[Node]

    def __init__(self, brokers: List[Node]):
        self.brokers = brokers


class FindRandomBrokersRequest(Message):
    pass


class FindRandomBrokersResponse(Message):
    brokers: List[Node]

    def __init__(self, brokers: List[Node]):
        self.brokers = brokers


class Connect(Message):
    broker: Node

    def __init__(self, broker: Node):
        self.broker = broker


class ConnectAck(Message):
    pass


class Sub(Message):
    topic: str

    def __init__(self, topic: str):
        self.topic = topic


class SubAck(Message):
    pass


class Unsub(Message):
    topic: str

    def __init__(self, topic: str):
        self.topic = topic


class UnsubAck(Message):
    pass


class Pub(Message):
    topic: str
    data: Any

    def __init__(self, topic: str, data: Any):
        self.topic = topic
        self.data = data


class PubAck(Message):
    pass


class Shutdown(Message):
    pass


class Protocol(object):
    env: simpy.Environment
    stores: Dict[Node, simpy.FilterStore]
    topology: Topology
    history: List[Message]
    enable_ack: bool
    logger: logging.Logger

    def __init__(self, env: simpy.Environment, topology: Topology, enable_ack=True):
        self.env = env
        self.stores = defaultdict(lambda: simpy.FilterStore(env))
        self.topology = topology
        self.history = list()
        self.enable_ack = enable_ack
        self.logger = logging.getLogger('protocol')

    def send(self, source: Node, destination: Node, message: MessageT):
        message.source = source
        message.destination = destination
        message.timestamp = self.env.now
        message.latency = self.topology.latency(source, destination)
        self.history.append(message)
        self.log(message)
        return self.stores[message.destination].put(message)
        # return self.env.all_of([
        #     self.env.timeout(int(math.ceil(message.latency))),
        #     self.stores[message.destination].put(message)
        # ])

    def receive(self, node: Node, *message_types: Type[MessageT]):
        if len(message_types) > 0:
            return self.stores[node].get(lambda m: type(m) in message_types)
        return self.stores[node].get()

    def log(self, message, *args):
        if self.logger.level > logging.DEBUG:
            return
        time = self.env.now
        minutes = int(time / 1000 / 60)
        seconds = int(time / 1000 % 60)
        self.logger.debug(f'{minutes:02d}:{seconds:02d} {message}', *args)
