from typing import Dict, Optional

from django.conf import settings
from django.db import models
from oscar.apps.catalogue.abstract_models import AbstractCategory

from oscar.core.loading import get_model, get_class
from .mixin import BitrixSyncMixin
from django.utils.translation import gettext as _

Product = get_model('catalogue', 'Product')
ProductAttribute = get_model('catalogue', 'ProductAttribute')  # == ProductProperty
# ProductProperty = get_model('catalogue', '')

Category = get_model('catalogue', 'Category')  # == Section

CategoryForm = get_class('dashboard.catalogue.forms', 'CategoryForm')


class ProductBX24(models.Model, BitrixSyncMixin):
    pass


class ProductPropertyBX24(models.Model, BitrixSyncMixin):
    pass


class ProductSectionBX24(models.Model, BitrixSyncMixin):
    """
    https://training.bitrix24.com/rest_help/crm/product_section/crm_productsection_fields.php
    """

    entity = "crm.productsection"

    bitrix_id = models.IntegerField(null=True, blank=True, verbose_name=_("Section ID"))

    name = models.CharField(max_length=256, verbose_name=_("Section name"))
    catalog_id = models.IntegerField(null=True, blank=True, verbose_name=_("Catalog ID"))
    section_id = models.IntegerField(null=True, blank=True, verbose_name=_("Associated section ID"))
    xml_id = models.CharField(null=True, blank=True, verbose_name=_("Mnemonic code"))

    category = models.ForeignKey(Category, null=True, blank=True, default=None, on_delete=models.CASCADE)

    fields_map = {
        "ID": "bitrix_id",
        "NAME": "name",
        "CATALOG_ID": "catalog_id",
        "SECTION_ID": "section_id",
        "XML_ID": "xml_id"
    }

    def update_or_create(self, data: Optional[Dict] = None) -> 'ProductSectionBX24':

        if data is None:
            data = {}

        b_id = data.pop('ID', None) or data.pop('id', None) or self.bitrix_id
        name = data.get('NAME') or data.get('name')

        obj, created = self.objects.update_or_create(
            bitrix_id=b_id,
            defaults={
                "name": name,
                "catalog_id": data.get("CATALOG_ID") or data.get('catalog_id'),
                "section_id": data.get("SECTION_ID") or data.get('section_id'),
                "xml_id": data.get("XML_ID") or data.get('xml_id')
            }
        )

        return obj

    @classmethod
    def update_or_create_cls(cls, data: Optional[Dict] = None) -> 'ProductSectionBX24':

        if data is None:
            data = {}

        b_id = data.pop('ID', None) or data.pop('id', None)
        name = data.get('NAME') or data.get('name')

        obj, created = cls.objects.update_or_create(
            bitrix_id=b_id,
            defaults={
                "name": name,
                "catalog_id": data.get("CATALOG_ID") or data.get('catalog_id'),
                "section_id": data.get("SECTION_ID") or data.get('section_id'),
                "xml_id": data.get("XML_ID") or data.get('xml_id')
            }
        )

        return obj

    def to_object(self, force_save=True) -> 'Category':
        category = self.category or Category(
            name=self.name,
            depth=1
        )
        parent = ProductSectionBX24.objects.filter(bitrix_id=self.section_id).first()

        parent = parent.category if parent else None

        if parent is not None:
            try:
                category.move(parent, 'first-child')
            except:
                pass

        if force_save:
            category.save()

        return category

    @staticmethod
    def from_object(obj: 'Category', force_save=True) -> 'ProductSectionBX24':
        """
        Get ProductSectionBX24 from Category
        :param obj:
        :param force_save:
        :return:
        """
        section = ProductSectionBX24.objects.filter(category=obj).first()

        if section:
            section.name = obj.name
        else:
            section = ProductSectionBX24(
                name=obj.name,
                category=obj,
                catalog_id=getattr(settings, 'BITRIX24_CATALOG_ID', None)
            )

        obj_parent = obj.get_parent()

        if obj_parent is not None:
            """
            Try get parent section_id from ProductSectionBX24 object
            """
            parent: 'ProductSectionBX24' = ProductSectionBX24.objects.filter(category=obj_parent).first()
            section.section_id = parent.bitrix_id if parent is not None else None

        if force_save:
            section.save()

        return section
