from django.utils.translation import gettext_lazy as _

from oscar.core.application import OscarConfig


class BitrixConfig(OscarConfig):
    label = 'bitrix'
    name = 'bitrix24_bridge'
    verbose_name = _('Bitrix24 Bridge')

    namespace = 'bitrix'

    def ready(self):
        super().ready()

    def get_urls(self):
        urls = super().get_urls()

        return self.post_process_urls(urls)
