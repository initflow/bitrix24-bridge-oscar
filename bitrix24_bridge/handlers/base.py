from typing import Dict


class BaseModelHandler:

    def handle(self, data: Dict):
        raise NotImplementedError

    class Meta:
        abstract = True
