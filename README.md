# GreenLedger V5

GreenLedger is a Flask-based carbon accounting and compliance app scaffold. It includes landing, modules, security, login, request access, and how-it-works pages with reusable Jinja components.

## Getting Started
1. **Install Python 3.12+** and `python3-venv`.
2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the app**
   ```bash
   python run.py
   ```
   App runs at `http://localhost:5000`.

## Environment Variables
Copy `.env` from the template and adjust as needed:
```
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
# DATABASE_URL (not in use yet)
```

## Routes
- `/` – Landing page
- `/modules` – Modules overview
- `/security` – Security & Trust
- `/how-it-works` – Educational guide
- `/request-access` – Access request form
- `/auth/login` – Login page (auth logic pending)

## Project Structure (key paths)
- `app/` – Flask app, factory, blueprints
- `templates/` – Jinja templates
  - `layouts/` – Base/auth layouts
  - `components/` – Reusable UI pieces (nav, cards, forms, etc.)
  - `pages/` – Page templates (landing, modules, security, how-it-works, login, request access)
- `static/` – CSS/JS/images
- `run.py` – App entry point
- `requirements.txt` – Python dependencies
- `.env` – Environment config (template)

## Notes
- Database integration is stubbed for future use.
- Header/footer are shared via components; page-specific content lives in `templates/pages/`.
- Tailwind is loaded via CDN in templates.
# GreenLedger_V5
