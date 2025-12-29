# Running the Development Server with HTTPS

This guide provides the steps to run the Django development server with a self-signed SSL certificate, which is necessary for testing the Mercado Libre OAuth2 handshake locally.

## 1. Install Dependencies

The `runserver_plus` command provided by `django-extensions` requires `Werkzeug` and `pyOpenSSL`. Install them using pip:

```bash
pip install django-extensions Werkzeug pyOpenSSL
```

## 2. Generate a Self-Signed Certificate

You need a self-signed certificate to serve your site over HTTPS. You can generate a key and a certificate file using `openssl`.

Run the following command in your project's root directory:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

This will create two files: `key.pem` (your private key) and `cert.pem` (your certificate). You can provide any information for the certificate fields; it doesn't matter for local development.

**Note:** Add `*.pem` to your `.gitignore` file to avoid committing these files to your repository.

## 3. Run the HTTPS Development Server

Now you can run the development server using `runserver_plus` and point it to your certificate files.

```bash
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 127.0.0.1:8000
```

Your server will now be running at `https://127.0.0.1:8000/`. You will likely see a security warning in your browser, which you can safely ignore for local development.

## 4. Verify the Mercado Libre Handshake

After running the server over HTTPS and completing the OAuth2 flow to get a token, you can use the management command `verify_ml_handshake` to test that the API connection is working correctly.

Open a new terminal and run:

```bash
python manage.py verify_ml_handshake
```

The script will fetch the token for the first user in your database and attempt to call the `/users/me` endpoint. It will print the status of the handshake verification.
