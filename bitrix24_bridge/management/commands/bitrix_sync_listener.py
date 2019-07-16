import logging
import re
from pprint import pprint

import ujson
from django.core.management.base import BaseCommand

from bitrix24_bridge.amqp.amqp import RabbitMQConsumer
from bitrix24_bridge.handlers import (
    ProductSectionHandler,
    ProductPropertyHandler,
    ProductHandler,
)

logger = logging.getLogger(__name__)


def regex_search(handlers: dict, key: str, default=None):
    for k, v in handlers.items():
        if re.match(k, key):
            return v

    return default


class DefaultHandler:
    def __call__(self, data, *args, **kwargs):
        pprint(data)

    def handler(self, data):
        pprint(data)


class Command(BaseCommand):
    help = 'Sync data with bitrix24'

    def __init__(self):
        super().__init__()
        self.msg_consumer = RabbitMQConsumer()

        self.HANDLERS = {
            'crm.productsection': ProductSectionHandler(),
            'crm.product.property': ProductPropertyHandler(),
            'crm.product': ProductHandler(),
            'default': DefaultHandler(),
        }

    def process_message(self, data: dict):

        entity = data.get('entity', 'default')

        handler = self.HANDLERS.get(entity)

        try:
            handler(data)
        except Exception as e:
            print(e)
            logger.error(str(e))

    def message_consume(self, channel, method_frame, header_frame, body):
        try:
            msg = ujson.loads(body)
            print(msg)
            self.process_message(msg)
            print("Message processed.")
        except Exception as e:
            print(e)
            logger.error(str(e))
        else:
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)

    def handle(self, *args, **options):
        self.msg_consumer.receive(self.message_consume)
