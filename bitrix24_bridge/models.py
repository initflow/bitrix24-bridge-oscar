import re
from decimal import Decimal
from typing import Dict, Optional, Tuple, List

from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.datetime_safe import datetime
from django.utils.translation import gettext as _

from bitrix24_bridge.mixin import BitrixSyncMixin
from oscar.core.loading import get_model

ProductAttribute = get_model('catalogue', 'ProductAttribute')  # == ProductProperty
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')

AttributeOption = get_model('catalogue', 'AttributeOption')
AttributeOptionGroup = get_model('catalogue', 'AttributeOptionGroup')

#


class ProductBX(models.Model, BitrixSyncMixin):
    entity = "crm.product"

    exclude_fields = {'id', 'bitrix_id', 'properties'},
    include_fields = {'ID': 'bitrix_id'}

    bitrix_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Product ID"))
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Product name"))

    active = models.CharField(max_length=16, default="Y", null=True, blank=True, verbose_name=_("Active"))

    # preview_picture = models.CharField

    sort = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Sort"))
    xml_id = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Mnemonic code"))

    # real type is DateTime
    timestamp_x = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("TIMESTAMP_X"))
    date_create = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("DATE_CREATE"))

    catalog_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Catalog ID"))
    section_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Associated section ID"))

    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))

    description_type = models.CharField(max_length=64, default="text", null=True, blank=True,
                                        verbose_name=_("Description type"))

    # real type Decimal
    price = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Price"))

    currency_id = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Currency id"))

    vat_id = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Vat id"))

    vat_included = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Vat included"))

    measure = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Measure"))

    properties = HStoreField(default=dict, null=True, blank=True, verbose_name=_("Custom properties"))

    product = models.ForeignKey('catalogue.Product', null=True, blank=True, on_delete=models.CASCADE)

    def process_properties(self, data: Optional[Dict] = None, force_save: bool = True):
        """
        Unpack self.properties from bitrix format
        Args:
            data:
            force_save:

        Returns:

        """
        if data is None:
            data = {}
        reg = re.compile(r'^PROPERTY_([\d]+)$')
        self.properties = {
            reg.search(k).group(1): v
            for k, v in data.items()
            if reg.match(k.strip().upper())
        }
        if force_save:
            self.save()

        return self.properties

    def get_properties(self, data: Optional[Dict] = None):
        """
        Pack self.properties in bitrix format
        Args:
            data:

        Returns:

        """
        data = data or self.properties
        reg = re.compile(r'^[\d]+$')

        return {
            f"PROPERTY_{k}": v
            for k, v in data.items()
            if reg.match(k)
        }

    def to_dict(self):
        """
        Add self.properties to dict representation
        Returns:

        """
        return dict(super().to_dict(), **self.get_properties())

    def update_or_create(self, data: Optional[Dict] = None):
        obj: ProductBX = super(self).update_or_create(data=data)

        obj.process_properties(data=data)

        return obj

    @classmethod
    def update_or_create_cls(cls, data: Optional[Dict] = None):
        obj: ProductBX = super().update_or_create_cls(data=data)

        obj.process_properties(data=data)
        return obj

    def to_object(self, force_save: bool = True):
        Product = get_model('catalogue', 'Product')
        ProductClass = get_model('catalogue', 'ProductClass')

        product = self.product or Product(
            product_class=ProductClass.objects.get_or_create(name="__bitrix_product_class")[0]
        )

        product.title = self.name
        product.description = self.description or ""

        # cary on Convert datetime
        try:
            product.date_created = datetime.fromisoformat(self.date_create)
        except Exception as e:
            pass
        try:
            product.date_updated = datetime.fromisoformat(self.timestamp_x)
        except Exception as e:
            pass

        if force_save:
            product.save()
            self.product = product
            self.save()

        if self.properties and product.id:
            """
            Don't save props without saved product
            """
            props: List[ProductPropertyBX] = (
                ProductPropertyBX.objects
                                 .prefetch_related('product_attribute')
                                 .filter(bitrix_id__in=self.properties.keys())
                                 .all()
            )

            for prop in props:
                """
                save_value() create new ProductAttributeValue or set if it exist
                """
                if prop.product_attribute:
                    try:
                        """
                        If data broken
                        """
                        prop.product_attribute.save_value(
                            product,
                            self.properties.get(prop.bitrix_id, {}).get('value')
                        )
                    except Exception as e:
                        pass

        section = ProductSectionBX.objects.filter(bitrix_id=self.section_id).first()

        if (section and section.category) and product.id:
            """
            Add category for product if it not exist
            """
            try:
                product.categories.add(section.category)
            except Exception as e:
                pass

        if self.price and product.id:
            StockRecord = get_model('partner', 'StockRecord')
            Partner = get_model('partner', 'Partner')

            partner, _ = Partner.objects.get_or_create(
                code="__bitrix24-bridge-partner"
            )

            stock_record, _ = StockRecord.objects.get_or_create(
                partner=partner,
                product=product,
                partner_sku=self.bitrix_id,
            )

            stock_record.price_excl_tax = Decimal(self.price)
            stock_record.price_currency = self.currency_id

            stock_record.save()

        return self.product

    @staticmethod
    def from_object(obj, force_save: bool = True):
        """
        Get ProductBX from Product
        :param obj: Product
        :param force_save: bool
        :return:
        """
        product = (
                ProductBX.objects.filter(product=obj).first()
                or ProductPropertyBX()
        )

        product.name = obj.title
        product.description = obj.description or ""

        """
        Take the deepest Section  
        """
        product.section_id = (
            ProductSectionBX.objects
                .values_list('bitrix_id', flat=True)
                .filter(category__in=obj.categories)
                .order_by('-category__depth')
                .first()
        )

        # cary on Convert datetime
        try:
            product.date_create = obj.date_created.isoformat()
        except Exception as e:
            pass
        try:
            product.timestamp_x = obj.date_updated.isoformat()
        except Exception as e:
            pass

        # attributes = obj.attribute.get_queryset()

        objs = (
            ProductPropertyBX.objects
                .values_list('bitrix_id', 'product_attribute__productattributevalue')
                .filter(product_attribute__product=obj)
        )

        if obj:
            product.properties = {
                bid: {
                    "VALUE": pav.value
                }
                for bid, pav in objs
            }

        """
        Try get price with currency
        """
        Partner = get_model('partner', 'Partner')
        partner, _ = Partner.objects.get_or_create(
            code="__bitrix24-bridge-partner"
        )
        StockRecord = get_model('partner', 'StockRecord')
        stock_record = StockRecord.objects.filter(partner=partner, product=obj).first()

        if stock_record:
            product.price = str(stock_record.price_excl_tax)
            product.currency_id = str(stock_record.price_currency)

        if force_save:
            product.save()

        return product


class ProductPropertyBX(models.Model, BitrixSyncMixin):
    entity = "crm.product.property"

    bitrix_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Product ID"))
    name = models.CharField(max_length=256, verbose_name=_("Product name"))

    iblock_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("IBlock id"))

    active = models.CharField(max_length=64, default="Y", null=True, blank=True, verbose_name=_("Active"))

    sort = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Sort"))

    default_value = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_("Default Value"))

    property_type = models.CharField(max_length=64, verbose_name=_("Property ype"))

    row_count = models.CharField(max_length=128, default=1, null=True, blank=True, verbose_name=_("Row count"))

    col_count = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Col count"))

    multiple = models.CharField(max_length=64, default="N", null=True, blank=True, verbose_name=_("Multiple"))

    xml_id = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Mnemonic code"))

    file_type = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("File type"))

    link_iblock_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Link iblock id"))

    is_required = models.CharField(max_length=256, null=True, blank=True, default="N", verbose_name=_("Is required"))

    user_type = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("User Type"))

    user_type_settings = HStoreField(default=dict, null=True, blank=True, verbose_name=_("User Type settings"))

    values = HStoreField(default=dict, null=True, blank=True, verbose_name=_("Values"))

    product_attribute = models.ForeignKey('catalogue.ProductAttribute', null=True, blank=True, on_delete=models.CASCADE)

    # f'{PROPERTY_TYPE}_{USER_TYPE}'
    TYPE_MAPS = {
        "S": ProductAttribute.TEXT,
        "N": ProductAttribute.INTEGER,
        "L": ProductAttribute.OPTION,
        "F": ProductAttribute.FILE,
        "S_Date": ProductAttribute.DATE,
        "S_DateTime": ProductAttribute.DATETIME,
    }

    def get_oscar_type(self, property_type: str, user_type: str) -> str:
        key: str = property_type + (f"_{user_type}" if user_type else "")
        return self.TYPE_MAPS.get(key, ProductAttribute.TEXT)

    def get_bitrix_type(self, oscar_type: str) -> Tuple[str, str]:
        """
        Args:
            oscar_type: str

        Returns:
            Tuple[str, str] = Tuple[property_type, user_type]
        """
        result = ("S", "")
        oscar_type = oscar_type.strip()
        for k, v in self.TYPE_MAPS.items():
            if oscar_type == v:
                result = f"{k}_".split('_')[:2]
                break
        return result

    def to_object(self, force_save: bool = True):

        attribute: ProductAttribute = self.product_attribute or ProductAttribute()

        attribute.name = self.name
        attribute.code = self.bitrix_id
        attribute.required = self.is_required == 'Y'
        attribute.type = self.get_oscar_type(self.property_type, self.user_type)

        if self.values:
            """
            try create options variants
            """
            try:
                option_group = attribute.option_group or AttributeOptionGroup(name=self.name)
                option_group.save()

                attribute.option_group = option_group

                option_group.options.get_queryset().delete()

                options = [
                    AttributeOption(option=option.get("VALUE"), group=option_group)
                    for option in self.values.values()
                ]
                AttributeOption.objects.bulk_create(options)
            except Exception as e:
                pass

        if force_save:
            attribute.save()
            self.product_attribute = attribute
            self.save()

        return self.product_attribute

    @classmethod
    def from_object(cls, obj: 'ProductAttribute', force_save: bool = True):
        """
        Get ProductSectionBX24 from Category
        :param obj:
        :param force_save:
        :return:
        """
        prop = (
                ProductPropertyBX.objects.filter(product_attribute=obj).first()
                or ProductPropertyBX()
        )

        prop.name = obj.name
        prop.is_required = "Y" if obj.required else "N"
        prop.property_type, prop.user_type = cls().get_bitrix_type(obj.type)

        if obj.type == ProductAttribute.OPTION:
            options = obj.option_group.options.get_queryset() if obj.option_group else []

            prop.values = {
                f"n{i}": {
                    "VALUE": op.option
                }
                for i, op in enumerate(options)
            }

        if force_save:
            prop.save()

        return prop


class ProductSectionBX(models.Model, BitrixSyncMixin):
    """
    https://training.bitrix24.com/rest_help/crm/product_section/crm_productsection_fields.php
    """

    entity = "crm.productsection"
    exclude_fields = {'id', 'category', 'bitrix_id'}
    include_fields = {'ID': 'bitrix_id'}

    bitrix_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Section ID"))

    name = models.CharField(max_length=256, verbose_name=_("Section name"))
    catalog_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Catalog ID"))
    section_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Associated section ID"))
    xml_id = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Mnemonic code"))

    category = models.ForeignKey('catalogue.Category', null=True, blank=True, default=None,
                                 on_delete=models.CASCADE)

    def to_object(self, force_save=True):
        Category = get_model('catalogue', 'Category')  # == Section

        category = self.category or Category(
            name=self.name,
            depth=1
        )
        parent = ProductSectionBX.objects.filter(bitrix_id=self.section_id).first()

        category_parent = parent.category if parent else None

        if category.id is not None and category_parent is not None:
            try:
                category.move(category_parent, 'first-child')
            except Exception as e:
                pass
        elif category.id is None:
            try:
                if category_parent is None:
                    Category.add_root(instance=category)
                else:
                    category_parent.add_child(instance=category)
            except Exception as e:
                pass

        if force_save:
            category.save()
            self.category = category
            self.save()

        return self.category

    @staticmethod
    def from_object(obj: 'Category', force_save=True):
        """
        Get ProductSectionBX24 from Category
        :param obj:
        :param force_save:
        :return:
        """
        section = ProductSectionBX.objects.filter(category=obj).first()

        if section:
            section.name = obj.name
        else:
            section = ProductSectionBX(
                name=obj.name,
                category=obj,
                catalog_id=getattr(settings, 'BITRIX24_CATALOG_ID', None)
            )

        obj_parent = obj.get_parent()

        if obj_parent is not None:
            """
            Try get parent section_id from ProductSectionBX24 object
            """
            parent = ProductSectionBX.objects.filter(category=obj_parent).first()
            section.section_id = parent.bitrix_id if parent is not None else None

        if force_save:
            section.save()

        return section
