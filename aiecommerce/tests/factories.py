import datetime

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from aiecommerce.models.product import ProductMaster, ProductRawPDF, ProductRawWeb

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

    distributor_code = factory.Faker("ean", length=13)
    raw_description = factory.Faker("text")
    image_url = factory.Faker("url")
    raw_html = "<html><body><p>Test HTML</p></body></html>"
    search_term = factory.Faker("word")
    created_at = factory.Faker("date_time", tzinfo=datetime.timezone.utc)


class ProductMasterFactory(DjangoModelFactory):
    class Meta:
        model = ProductMaster

    code = factory.Faker("ean", length=13)
    description = factory.Faker("text")
    category = factory.Faker("word")
    price = factory.Faker("pydecimal", left_digits=8, right_digits=2, positive=True)
    is_active = factory.Faker("pybool")
    last_updated = factory.Faker("date_time", tzinfo=datetime.timezone.utc)


class MercadoLibreListingFactory(DjangoModelFactory):
    class Meta:
        model = "aiecommerce.MercadoLibreListing"

    product = factory.SubFactory(ProductMasterFactory)
    ml_id = factory.Sequence(lambda n: f"MCO{100000 + n}")
    status = "PENDING"
