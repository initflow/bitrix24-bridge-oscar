from typing import Tuple, Dict, Optional, List, Set, Iterable

from bitrix24_bridge.amqp.amqp import RabbitMQProducer


class BitrixSyncMixin:
    """

    bitrix_id: int - object id in bitrix system

    :param entity: str - e.g. 'crm.product'
    """
    entity: str = None

    bitrix_id = None  # ID in bitrix24 system

    methods: Iterable[str] = {'list', 'add', 'get', 'delete', 'update'}
    fields_map = None

    exclude_fields: Optional[Iterable[str]] = None
    include_fields: Optional[Dict[str, str]] = None

    def get_sync_object(self, bitrix_id: int):
        obj = self.objects.filter(bitrix_id=bitrix_id).first()
        return obj

    def update_or_create(self, data: Optional[Dict] = None):
        """
        Update instance depend on fields map
        Args:
            data:

        Returns:

        """
        if data is None:
            data = {}

        b_id = data.pop('ID', None) or data.pop('id', None) or self.bitrix_id

        obj, created = self.__class__.objects.update_or_create(
            bitrix_id=b_id,
            defaults={
                o_f: data.get(b_f, getattr(self, o_f, None))
                for b_f, o_f in self.get_map()
            }
        )

        return obj

    @classmethod
    def update_or_create_cls(cls, data: Optional[Dict] = None):

        if data is None:
            data = {}

        b_id = data.pop('ID', None) or data.pop('id', None)

        obj, created = cls.objects.update_or_create(
            bitrix_id=b_id,
            defaults={
                o_f: data.get(b_f)
                for b_f, o_f in cls().get_map()
                if data.get(b_f) is not None
            }
        )

        return obj

    def get_or_create(self, data: Optional[Dict] = None):
        if data is None:
            data = {}

        b_id = data.pop('ID', None) or data.pop('id', None) or self.bitrix_id

        obj, created = self.__class__.objects.get_or_create(
            bitrix_id=b_id,
            defaults={
                o_f: data.get(b_f, getattr(self, o_f, None))
                for b_f, o_f in self.get_map()
            }
        )

        return obj

    def generate_map(self, *, include: Optional[Dict[str, str]] = None, exclude: Optional[Iterable[str]] = None):
        """
        Generate fields map from django.Model fields

        exclude related fields

        Args:
            include: Dict[str, str] - dict of (bitrix_name, oscar_name)
            exclude: Iterable[str] - prefer Set[str]

        Returns:

        """
        if include is None: include = {}
        if exclude is None: exclude = set()
        return {
            **{
                str(f.name).upper(): f.name
                for f in self._meta.get_fields()
                if f not in exclude and not f.is_relation
            },
            **include
        }

    def get_map(self) -> Dict[str, str]:
        if self.fields_map is None:
            try:
                self.fields_map = self.generate_map(
                    exclude=self.exclude_fields or {'id', 'bitrix_id'},
                    include=self.include_fields or {'ID': 'bitrix_id'}
                )
            except:
                pass
        return self.fields_map

    def to_dict(self):
        return {
            b_f: getattr(self, o_f, None)
            for b_f, o_f in self.get_map().items()
        }

    def to_object(self, force_save: bool = True):
        raise NotImplementedError

    @staticmethod
    def from_object(obj, force_save: bool = True):
        raise NotImplementedError

    @staticmethod
    def send_command(
            method: str,
            params: Optional[Dict] = None,
            action: Optional[str] = None,
            meta: Optional[Dict] = None
    ) -> Optional[bool]:
        producer = RabbitMQProducer()

        data = {
            "method": method,
            "action": action,
            "params": params,
            "meta": meta
        }

        try:
            producer.send(data)
            response = True
        except Exception as e:
            response = False
        finally:
            producer.close()

        return response

    def list(self, params: Optional[Dict] = None, action: Optional[str] = None, meta: Optional[Dict] = None):
        method = f"{self.entity}.list"
        action = action or 'list'
        return self.send_command(method=method, params=params, action=action, meta=meta)

    def batch(self, params: Optional[Dict] = None, action: Optional[str] = None, meta: Optional[Dict] = None):
        method = f"{self.entity}.list"
        action = action or 'batch'
        return self.send_command(method=method, params=params, action=action, meta=meta)

    def add(self, params: Optional[Dict] = None, action: Optional[str] = None, meta: Optional[Dict] = None):
        method = f"{self.entity}.add"
        params = params or {
            "fields": self.to_dict()
        }
        return self.send_command(method=method, params=params, action=action, meta=meta)

    def get(self, bid: int = None, action: Optional[str] = None, meta: Optional[Dict] = None):
        method = f"{self.entity}.get"
        params = {
            "id": bid or self.bitrix_id
        }

        if params.get('id') is None:
            return False

        return self.send_command(method=method, params=params, action=action, meta=meta)

    def delete(self, bid: int = None, action: Optional[str] = None, meta: Optional[Dict] = None):
        method = f"{self.entity}.delete"

        params = {
            "id": bid or self.bitrix_id
        }

        if params.get('id') is None:
            return False

        return self.send_command(method=method, params=params, action=action, meta=meta)

    def update(self, params: Optional[Dict] = None, action: Optional[str] = None, meta: Optional[Dict] = None):
        method = f"{self.entity}.update"

        params = params or {
            "id": self.bitrix_id,
            "fields": self.to_dict()
        }

        if params.get('id') is None:
            params.pop('id', None)
            return self.add(params=params)

        return self.send_command(method=method, params=params, action=action, meta=meta)

    def types(self, params: Optional[Dict] = None, action: Optional[str] = None, meta: Optional[Dict] = None):
        method = f"{self.entity}.types"
        return self.send_command(method=method, params=params, action=action, meta=meta)
