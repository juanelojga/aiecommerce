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

#### 1. Overview

Mercado Libre does not provide a traditional, isolated sandbox environment. All testing, including integration and end-to-end testing, is performed directly on the production API. To facilitate this without impacting real data, we use **"Test Users"**. These are special accounts that operate on the live platform but are flagged for testing purposes.

#### 2. Generating Test Users

Test users are created and managed via a dedicated management command. This process requires a valid production user's token to authorize the creation of test accounts.

**Command:**
```bash
python manage.py create_ml_test_user --site=MEC
```

**Process:**
1.  The command uses an existing, valid production `MercadoLibreToken` to call the test user creation endpoint.
2.  Upon successful creation, it saves the new test user's credentials (token, refresh token, etc.) to the `mercadolibre_token` table.
3.  The `is_test_user` flag is automatically set to `True` for these credentials, distinguishing them from production tokens.

**Important:** For comprehensive end-to-end testing, it is crucial to generate both a **Seller** and a **Buyer** test user. This allows for simulating the full e-commerce lifecycle, from listing a product to making a purchase.

#### 3. Using the Sandbox Mode

Our system implements a "Dual-Layer" approach to safely interact with the Mercado Libre API. Management commands that can perform write operations are equipped with a `--sandbox` flag.

**Example Command:**
```bash
python manage.py verify_ml_handshake --sandbox
```

**How it works:**
- When the `--sandbox` flag is present, the service layer is instructed to disregard production tokens.
- The system automatically queries the database for a `MercadoLibreToken` where `is_test_user` is `True` for the corresponding site (e.g., 'MEC').
- This ensures that all API operations for that command are executed exclusively under the context of a test user, preventing accidental changes to live data.

#### 4. Manual Verification

You can use the credentials of a generated test user to log in to the Mercado Libre web portal and manually verify the state of your test environment.

**Steps:**
1.  When a test user is created, the command will output the `nickname` and `password`.
2.  Navigate to the appropriate Mercado Libre site (e.g., [mercadolibre.com.ec](https://mercadolibre.com.ec)).
3.  Log in using the test user's `nickname` and `password`.
4.  From here, you can manually inspect test listings, view purchase history, and verify that your integration is behaving as expected from a user's perspective.
