import json

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import ProductMaster
from aiecommerce.models.mercadolibre_token import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl import (
    AIAttributeFiller,
    CategoryAttributeFetcher,
    CategoryPredictorService,
    MercadoLibreClient,
)
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError


class Command(BaseCommand):
    help = "Test the Mercado Libre attribute pipeline for a given product."

    def add_arguments(self, parser):
        parser.add_argument("product_code", type=str, help="The code of the product to test.")
        parser.add_argument(
            "--site",
            type=str,
            default="MEC",
            help="The Mercado Libre site ID to use.",
        )

    def handle(self, *args, **options):
        product_code = options["product_code"]
        site_id = options["site"]

        try:
            product = ProductMaster.objects.get(code=product_code)
        except ProductMaster.DoesNotExist:
            raise CommandError(f'Product with code "{product_code}" does not exist.')

        self.stdout.write(self.style.NOTICE(f"Fetching token for site '{site_id}'..."))
        auth_service = MercadoLibreAuthService()
        try:
            # We first try to find the latest token to get a user_id
            token_instance = MercadoLibreToken.objects.filter(is_test_user=False).latest("created_at")
            # Then we use the auth_service to ensure it is valid (refreshes if needed)
            token_instance = auth_service.get_valid_token(user_id=token_instance.user_id)
        except MercadoLibreToken.DoesNotExist:
            raise CommandError(f"No token found for site '{site_id}'. Please authenticate first.")
        except MLTokenError as e:
            raise CommandError(f"Error retrieving valid token for site '{site_id}': {e}")

        client = MercadoLibreClient(access_token=token_instance.access_token)

        # Step 1: Predict Category
        self.stdout.write(self.style.NOTICE("Step 1: Predicting category..."))
        predictor = CategoryPredictorService(client, site_id=site_id)
        category_id = predictor.predict_category(product.seo_title or "")
        if not category_id:
            raise CommandError(f"Could not predict category for product '{product.seo_title}'")
        self.stdout.write(self.style.SUCCESS(f"Predicted Category: {category_id}"))

        # Step 2: Fetch Attributes
        self.stdout.write(self.style.NOTICE("Step 2: Fetching required attributes..."))
        fetcher = CategoryAttributeFetcher(client)
        attributes = fetcher.get_required_attributes(category_id)
        attribute_ids = [attr["id"] for attr in attributes]
        self.stdout.write(self.style.SUCCESS(f"Found {len(attributes)} attributes: {attribute_ids}"))
        print(f"Attributes: {attributes}")
        # Step 3: Fill Attributes
        self.stdout.write(self.style.NOTICE("Step 3: Filling attributes with AI..."))
        filler = AIAttributeFiller()
        result = filler.fill_and_validate(product, attributes)
        filled_attributes = result["attributes"]
        metadata = result["meta"]

        self.stdout.write(self.style.SUCCESS("--- AI Filler Results ---"))
        self.stdout.write("Confidence Metadata:")
        self.stdout.write(json.dumps(metadata, indent=2))

        if result.get("missing_required"):
            self.stdout.write(self.style.WARNING("Missing Required Attributes:"))
            self.stdout.write(json.dumps(result["missing_required"], indent=2))
        else:
            self.stdout.write(self.style.SUCCESS("All required attributes were filled."))

        self.stdout.write("Final Attributes Payload:")
        self.stdout.write(json.dumps(filled_attributes, indent=2))
