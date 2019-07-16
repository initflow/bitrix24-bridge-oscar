from bitrix24_bridge.handlers.base import BaseModelHandler
from bitrix24_bridge.models import ProductBX


class ProductHandler(BaseModelHandler):
    model = ProductBX
