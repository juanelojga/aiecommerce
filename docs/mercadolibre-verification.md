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
