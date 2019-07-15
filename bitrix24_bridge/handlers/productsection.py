from pprint import pprint
from typing import Dict, List


from ..models import ProductSectionBX24
from .base import BaseModelHandler


class ProductSectionHandler(BaseModelHandler):

    model = ProductSectionBX24

    def list(self, data: Dict):
        result: List[Dict] = data.get('result')

        if data.get('status_code') != 200:
            print(data)
            return

        for part in result:
            sync_obj = self.model.update_or_create_cls(part)
            category = sync_obj.to_object()

    def get(self, data: Dict):
        pass

    def update(self, data: Dict):
        pass

    def default(self, data: Dict):
        pprint(data)

    def dispatch(self, data: Dict):
        method = data.get('method', 'default')

        method = method.rsplit('.', 1)[-1]

        handler = getattr(self, method, self.default)

        try:
            handler(data)
        except Exception as e:
            pass

    def handle(self, data: Dict):
        """
        Main process method
        Args:
            data:

        Returns:

        """
        result: List[Dict] = data.get('result')

        for part in result:
            self.dispatch(part)
