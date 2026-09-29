# Personal Finance Advisor Bot

Personal Finance Advisor Bot is a production-quality Flask/Jinja2 personal-finance workspace for tracking income and expenses, planning category budgets, monitoring savings goals, generating monthly reports, and asking for educational AI guidance grounded in the signed-in user's own records.

## What is included

The application uses Flask's application-factory pattern and Blueprints, SQLAlchemy models compatible with SQLite and PostgreSQL-style deployments, Flask-Login, Werkzeug password hashing, Flask-WTF CSRF protection, Bootstrap 5, Chart.js, and a responsive fintech interface. It includes authentication and profile settings; income, expense, category, budget, and savings CRUD; a shared month selector; dashboard cards and charts; budget status indicators; AI recommendation history; advisor chat; monthly reports with print/PDF/CSV output; default categories; and an idempotent demo seed.

The AI service in `app/services/ai_service.py` supports Gemini first or OpenAI optionally through environment variables. It validates provider JSON and has a deterministic rule-based fallback for missing keys, timeouts, provider errors, or malformed responses. Recommendations are stored in the `AIRecommendation` table. Guidance is educational and is not regulated financial, tax, or investment advice.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python seed_data.py
.venv/bin/python run.py
```

The app listens on `http://127.0.0.1:3000` by default. The preview/deployment runtime uses `PORT=3000` and binds to `0.0.0.0`.

When running inside the cross-site Manus Preview iframe, start the service with `MANUS_PREVIEW=true` so session cookies use `Secure; SameSite=None`, allowing Flask-WTF CSRF tokens to persist across the Preview proxy. Ordinary local HTTP development should leave this unset or `false`.

## Demo account

- Email: `demo@financebot.com`
- Password: `DemoFinance123!`

The seeded account includes sample salary and freelance income, category-based expenses, an emergency-fund goal, and contribution history. `seed_data.py` is safe to run again; it does not duplicate the demo records.

## Environment and AI keys

Copy `.env.example` to `.env`. For the local demo, SQLite is used and AI fallback works without any provider key. To enable provider-backed responses, set:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
```

or:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
```

With `AI_PROVIDER=auto`, Gemini is tried when configured, then OpenAI, then the local fallback. API keys stay server-side and are never included in frontend HTML or JavaScript.

## Optional Ngrok

Ngrok is optional for local exposure. Add an authtoken and enable it in `.env`:

```dotenv
NGROK_AUTHTOKEN=your-ngrok-authtoken
USE_NGROK=true
```

`run.py` will print the tunnel URL on startup. For a durable public URL, publish the Webdev server deployment instead of relying on an ephemeral tunnel.

## Tests

```bash
.venv/bin/pytest -q
```

The test suite covers registration/login/logout and protected routes, income and expense CRUD, ownership isolation, rule-based AI fallback, AI budget generation, reports, dashboard chart payloads, database persistence, and Salaried/Student/Freelancer/Household persona handling.

## Main routes

Public: `/`, `/register`, `/login`, `/health`, `/manus-routes.json`.

Authenticated: `/dashboard`, `/income`, `/expenses`, `/categories`, `/budget`, `/savings`, `/advisor`, `/reports`, and `/profile`.

## Deployment notes

The app is server-rendered Flask and should be deployed as an application container with a health check at `/health`. Set a strong `SECRET_KEY`, use a durable PostgreSQL-compatible `DATABASE_URL` for production persistence, keep secure cookies enabled, and never commit `.env`, the SQLite database, or provider credentials. The included `app/static/manus-routes.json` is served at the required origin-root route for route verification.
