# Bitrix24-bridge-oscar plugin

## Install

> pip install git+https://github.com/initflow/bitrix24-bridge-oscar

or 

> pip install ssh+git@github.com/initflow/bitrix24-bridge-oscar.git

Add to django settings connection settings for Rabbitmq

```python
BB_RABBITMQ_HOST = "rabbit_host"
BB_RABBITMQ_VIRTUAL_HOST = "virtual_host" or "/" or None
BB_RABBITMQ_PORT = "rabbit_port" or "5672" or None
BB_RABBITMQ_USER = "rabbit_user"
BB_RABBITMQ_PASS = "rabbit_password"
BB_RABBITMQ_EXCHANGE = "your_castom_exchange" or "bitrix24"
BB_RABBITMQ_ROUTING_KEY = "rabbitmq_routing_key" or "send.command"
BB_RABBITMQ_MESSAGE_QUEUE = "rabbitmq_info_queue" or "bitrix24-info"
BB_RABBITMQ_QUEUE_DURABLE = "rabbitmq_queue_durable" or True
BB_RABBITMQ_EXCHANGE_DURABLE = "rabbitmq_exchange_durable" or True
BB_RABBITMQ_EXCHANGE_TYPE = "rabbitmq_exchange_type" or "TOPIC" or None
BB_RABBITMQ_COMMAND_QUEUE = 'rabbitmq_command_queue' or "bitrix24-command"
```

Migrate bitrix models

> python manage.py migrate bitrix24_bridge

## HOWTO


