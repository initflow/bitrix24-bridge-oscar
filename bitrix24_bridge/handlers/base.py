from pprint import pprint
from typing import Dict, List


class BaseModelHandler:

    model = None

    def list(self, data: Dict):
        result: List[Dict] = data.get('result')

        if data.get('status_code') != 200:
            print(data)
            return

        for part in result:
            sync_obj = self.model.update_or_create_cls(part)
            oscar_obj = sync_obj.to_object()

    def get(self, data: Dict):
        result: Dict = data.get('result')

        if data.get('status_code') != 200:
            print(data)
            return

        sync_obj = self.model.update_or_create_cls(result)
        oscar_obj = sync_obj.to_object()

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
            print(e)

    def handle(self, data: Dict, *args, **kwargs):
        """
        Main process method
        Args:
            data:

        Returns:

        """
        result: List[Dict] = data.get('result')

        for part in result:
            self.dispatch(part)

    def __call__(self, data: Dict, *args, **kwargs):
        return self.handle(data, *args, **kwargs)

