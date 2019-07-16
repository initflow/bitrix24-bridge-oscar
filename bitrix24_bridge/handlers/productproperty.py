from bitrix24_bridge.handlers.base import BaseModelHandler
from bitrix24_bridge.models import ProductPropertyBX


class ProductPropertyHandler(BaseModelHandler):
    model = ProductPropertyBX
