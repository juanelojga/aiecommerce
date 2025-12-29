### Verifying Mercado Libre Credentials and Tokens

To verify that the Mercado Libre OAuth2 flow was successful and that your credentials are valid, you can use the `MercadoLibreAuthService` and `MercadoLibreClient`.

Below is an example of how to manually verify the handshake in a Django shell or a script.

#### Python Example

```python
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.models import MercadoLibreToken

# 1. Get the stored user ID
user_id = MercadoLibreToken.objects.first().user_id

# 2. Use the Auth Service to get a valid token (handles auto-refresh if needed)
auth_service = MercadoLibreAuthService()
token_record = auth_service.get_valid_token(user_id)

client = MercadoLibreClient(access_token=token_record.access_token)
me_data = client.get("users/me")

print(f"Handshake Verified! Connected as: {me_data['nickname']} ({me_data['email']})")
```

#### Using the Management Command

Alternatively, you can use the built-in management command:

```bash
python manage.py verify_ml_handshake
```

This command performs the same steps as the example above and outputs the results to the console.

### Testing with Mercado Libre (Sandbox Strategy)

There is no separate "sandbox" environment for Mercado Libre integrations in this project. Instead, testing is conducted directly against the production API using **"Test Users"**. This approach ensures that our integrations behave consistently with the live environment.

#### Creating Mercado Libre Test Users

To set up a test user, use the following management command:

```bash
python manage.py create_ml_test_user --site=MEC
```

This command will guide you through the OAuth2 authentication flow for a new Mercado Libre test user and store their credentials in the database.

#### Safe Testing with the `--sandbox` Flag

For commands that involve publishing or modifying data on Mercado Libre, a `--sandbox` flag is available. When this flag is used, the command will ensure that all operations are performed under the context of a Mercado Libre Test User (if available and configured for the given site). This prevents accidental modifications to real production listings or accounts.

Developers should always use the `--sandbox` flag when testing publication workflows to isolate test data from actual production data.
