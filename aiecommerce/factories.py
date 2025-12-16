import datetime

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from .models.product import ProductMaster, ProductRawPDF, ProductRawWeb

fake = Faker()


class ProductRawPDFFactory(DjangoModelFactory):
    class Meta:
        model = ProductRawPDF

    raw_description = factory.Faker("text")
    distributor_price = factory.Faker("pydecimal", left_digits=8, right_digits=2, positive=True)
    category_header = factory.Faker("word")
    created_at = factory.Faker("date_time", tzinfo=datetime.timezone.utc)


class ProductRawWebFactory(DjangoModelFactory):
    class Meta:
        model = ProductRawWeb

    sku = factory.Faker("ean", length=13)
    raw_description = factory.Faker("text")
    scraped_availability = factory.Faker("text", max_nb_chars=50)
    product_url = factory.Faker("url")
    raw_html = "<html><body><p>Test HTML</p></body></html>"
    search_term = factory.Faker("word")
    created_at = factory.Faker("date_time", tzinfo=datetime.timezone.utc)


class ProductMasterFactory(DjangoModelFactory):
    class Meta:
        model = ProductMaster

    sku = factory.Faker("ean", length=13)
    description = factory.Faker("text")
    brand = factory.Faker("company")
    price_distributor = factory.Faker("pydecimal", left_digits=8, right_digits=2, positive=True)
    availability_status = factory.Faker("word")
    last_updated = factory.Faker("date_time", tzinfo=datetime.timezone.utc)
