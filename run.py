import os

from app import create_app

app = create_app()


def run():
    port = int(os.getenv("PORT", "3000"))
    host = os.getenv("HOST", "0.0.0.0")
    if app.config.get("USE_NGROK") and app.config.get("NGROK_AUTHTOKEN"):
        try:
            from pyngrok import ngrok
            ngrok.set_auth_token(app.config["NGROK_AUTHTOKEN"])
            tunnel = ngrok.connect(port, bind_tls=True)
            print(f"Ngrok public URL: {tunnel.public_url}")
        except Exception as exc:
            print(f"Ngrok unavailable; continuing locally: {exc}")
    print(f"Personal Finance Advisor Bot listening on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run()
