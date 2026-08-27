import webbrowser
from config.settings import settings

try:
    from fyers_apiv3 import fyersModel
    HAS_SDK = True
except ImportError:
    HAS_SDK = False

def run_fyers_login():
    """
    Automated Fyers OAuth Login Helper:
    1. Opens the Fyers login URL in your browser.
    2. Prompts you to paste the redirected auth_code.
    3. Exchanges it for an Access Token and saves it to .env.
    """
    print("=" * 60)
    print("🚀 ANIL BABU TRADES - FYERS API v3 OAUTH GENERATOR")
    print("=" * 60)

    client_id = settings.FYERS_APP_ID or input("Enter Fyers App ID (e.g. XCXXXXX-100): ").strip()
    secret_key = getattr(settings, "FYERS_SECRET_KEY", "") or input("Enter Fyers Secret Key: ").strip()
    redirect_uri = getattr(settings, "FYERS_REDIRECT_URI", "https://127.0.0.1:8000/api/fyers/callback")

    if not HAS_SDK:
        print("⚠️ fyers_apiv3 library not installed. Install with: pip install fyers-apiv3")
        return

    session = fyersModel.SessionModel(
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type="code",
        state="anil_babu_trades",
        secret_key=secret_key,
        grant_type="authorization_code"
    )

    auth_url = session.generate_authcode()
    print("\n🌐 Opening Fyers Login URL in your default browser:")
    print(auth_url)
    webbrowser.open(auth_url, new=1)

    print("\n👉 Please log in, authorize the app, and paste the 'auth_code' from the redirected URL:")
    auth_code = input("\nEnter auth_code: ").strip()

    if not auth_code:
        print("❌ Error: No auth code provided.")
        return

    session.set_token(auth_code)
    response = session.generate_token()

    if "access_token" in response:
        token = response["access_token"]
        print("\n🎉 SUCCESS! Access Token Generated Successfully:")
        print(f"Token: {token[:20]}...{token[-10:]}")
        print("\nSaving to .env...")

        # Update .env
        env_path = ".env"
        lines = []
        try:
            with open(env_path, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            pass

        token_updated = False
        new_lines = []
        for line in lines:
            if line.startswith("FYERS_ACCESS_TOKEN="):
                new_lines.append(f"FYERS_ACCESS_TOKEN={token}\n")
                token_updated = True
            elif line.startswith("FYERS_APP_ID=") and client_id:
                new_lines.append(f"FYERS_APP_ID={client_id}\n")
            else:
                new_lines.append(line)

        if not token_updated:
            new_lines.append(f"FYERS_ACCESS_TOKEN={token}\n")
            new_lines.append(f"FYERS_APP_ID={client_id}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

        print("✅ .env updated successfully! Your trading engine is now ready for live Fyers v3 execution.")
    else:
        print("\n❌ Failed to generate token. Response:", response)

if __name__ == "__main__":
    run_fyers_login()
