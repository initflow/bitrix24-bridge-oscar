import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pika
import ujson
from django.conf import settings
from typing import Callable, Any, Optional, List

"""
BB = Bitrix24 Bridge
"""


def get_var(name) -> Callable[[], Optional[Any]]:
    """
    Safe wraper over settings
    :param name:
    :return: Callable[[], Optional[Any]] - get param from settings if it defined, else return None
    """
    return functools.partial(getattr, settings, name, None)


class MessageProducer(ABC):

    @abstractmethod
    def connect(self):
        raise NotImplemented

    @abstractmethod
    def close(self):
        raise NotImplemented

    @abstractmethod
    def send(self, message):
        raise NotImplemented

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    class Meta:
        abstract = True


@dataclass
class RabbitMQProducer(MessageProducer):
    connection_url: Optional[str] = field(default_factory=get_var('BB_RABBITMQ_URL'))

    host: str = field(default_factory=get_var('BB_RABBITMQ_HOST'))
    port: int = field(default_factory=get_var('BB_RABBITMQ_PORT'))

    virtual_host: str = field(default_factory=get_var('BB_RABBITMQ_VIRTUAL_HOST'))

    user: str = field(default_factory=get_var('BB_RABBITMQ_USER'))
    password: str = field(default_factory=get_var('BB_RABBITMQ_PASS'))

    routing_key: str = field(default_factory=get_var('BB_RABBITMQ_ROUTING_KEY'))
    exchange: str = field(default_factory=get_var('BB_RABBITMQ_EXCHANGE'))
    exchange_type: str = field(default_factory=get_var('BB_RABBITMQ_EXCHANGE_TYPE'))
    exchange_durable: str = field(default_factory=get_var('BB_RABBITMQ_EXCHANGE_DURABLE'))

    connection: Optional[pika.BlockingConnection] = None

    def connect(self):
        if self.connection is None or self.connection.is_closed:
            credentials = pika.PlainCredentials(self.user, self.password)
            if self.connection_url:
                conn_params = pika.URLParameters(self.connection_url)
            else:
                conn_params = pika.ConnectionParameters(self.host, self.port, self.virtual_host, credentials)
            self.connection = pika.BlockingConnection(parameters=conn_params)
        return self.connection

    def close(self):
        if self.connection.is_open:
            self.connection.close()

    def send(self, message):
        channel = self.connect().channel()
        channel.basic_publish(
            self.exchange,
            self.routing_key,
            ujson.dumps(message),
            pika.BasicProperties(
                content_type='application/json; charset=utf-8'
            ))


class MessageConsumer(ABC):

    @abstractmethod
    def connect(self):
        raise NotImplemented

    @abstractmethod
    def close(self):
        raise NotImplemented

    @abstractmethod
    def receive(self, message):
        raise NotImplemented

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    class Meta:
        abstract = True


@dataclass
class RabbitMQConsumer(MessageConsumer):
    connection_url: Optional[str] = field(default_factory=get_var('BB_RABBITMQ_URL'))

    host: str = field(default_factory=get_var('BB_RABBITMQ_HOST'))
    port: int = field(default_factory=get_var('BB_RABBITMQ_PORT'))

    virtual_host: str = field(default_factory=get_var('BB_RABBITMQ_VIRTUAL_HOST'))

    user: str = field(default_factory=get_var('BB_RABBITMQ_USER'))
    password: str = field(default_factory=get_var('BB_RABBITMQ_PASS'))

    queue: str = field(default_factory=get_var('BB_RABBITMQ_SEND_MESSAGE_QUEUE'))
    routing_key: str = field(default_factory=get_var('BB_RABBITMQ_ROUTING_KEY'))
    exchange: str = field(default_factory=get_var('BB_RABBITMQ_EXCHANGE'))
    exchange_type: str = field(default_factory=get_var('BB_RABBITMQ_EXCHANGE_TYPE'))
    exchange_durable: str = field(default_factory=get_var('BB_RABBITMQ_EXCHANGE_DURABLE'))

    connection: Optional[pika.BlockingConnection] = field(init=False, repr=False, compare=False)

    buffer: List = field(init=False, repr=False, compare=False, default_factory=list)

    def connect(self):
        if self.connection is None or self.connection.is_closed:
            credentials = pika.PlainCredentials(self.user, self.password)
            if self.connection_url:
                conn_params = pika.URLParameters(self.connection_url)
            else:
                conn_params = pika.ConnectionParameters(
                    host=self.host, port=self.port,
                    virtual_host=self.virtual_host,
                    credentials=credentials,
                )
            self.connection = pika.BlockingConnection(parameters=conn_params)

        return self.connection

    def default_callback(self, channel, method_frame, header_frame, body):
        try:
            msg = ujson.loads(body)
        except Exception:
            msg = "¯\_(ツ)_/¯"
        self.buffer.append(msg)

    def close(self):
        if self.connection and self.connection.is_open():
            self.connection.close()

    def receive(self, callback=None):
        if callback is None:
            callback = self.default_callback

        connection = self.connect()
        channel = connection.channel()
        channel.basic_consume(self.queue, callback)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()

