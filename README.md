# GreenLedger V5

GreenLedger is a Flask-based carbon accounting and compliance app scaffold. It includes landing, modules, security, login, request access, and how-it-works pages with reusable Jinja components.

## Getting Started

### 1. Install Python 3.12+ and Dependencies
```bash
# Install python3-venv (if not already installed)
sudo apt install python3.12-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Reset database and seed with mock data
python scripts/reset_db_and_seed.py
```

### 3. Run the App
```bash
source venv/bin/activate
python run.py
```

App runs at `http://localhost:5000`.

### 4. Login with Mock Users

**Acme Global Industries:**
- Admin: `admin@acme.com` / `admin123`
- Auditor: `auditor@acme.com` / `auditor123`
- Worker: `worker@acme.com` / `worker123`
- Viewer: `viewer@acme.com` / `viewer123`

**EuroSteel Corp:**
- Admin: `admin@eurosteel.com` / `admin123`
- Worker: `worker@eurosteel.com` / `worker123`

**GreenTech Solutions:**
- Admin: `admin@greentech.com` / `admin123`

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

## Project Structure

### Application Structure (`app/`)
- `core/` – Core application components (auth, config, extensions, utils)
- `features/` – Feature modules (emissions, cbam, reports, data_collection, explorer)
- `dashboards/` – User-type specific dashboards (admin, user, auditor)
- `shared/` – Shared components (decorators, middleware, exceptions)
- `api/` – REST API layer (v1)
- `models/` – Database models
- `main.py` – Public routes (landing, modules, etc.)
- `factory.py` – Application factory

### Templates (`templates/`)
- `layouts/` – Base/auth layouts
- `components/` – Reusable UI pieces (nav, cards, forms, charts, etc.)
- `pages/` – Page templates (landing, modules, security, explorer, etc.)

### Static Assets (`static/`)
- `css/` – Stylesheets
- `js/` – JavaScript files
- `images/` – Image assets
- `documents/pdf/` – Generated PDF documents

### Documentation (`docs/`)
- `whitepapers/` – Technical and security whitepapers
- `api/` – API documentation
- `user-guides/` – User documentation
- `technical/` – Technical documentation (architecture, deployment, development)
- `legal/` – Legal documents (terms, privacy policy)

### Scripts (`scripts/`)
- `reset_db_and_seed.py` – Script to reset database and seed mock data
- `generate_pdfs.py` – Script to generate PDFs from Markdown documentation

## Documentation

### Generating PDFs

PDF documents can be generated from Markdown sources:

```bash
# Install dependencies
pip install markdown pdfkit

# Install wkhtmltopdf (required for PDF generation)
# Ubuntu/Debian: sudo apt-get install wkhtmltopdf
# macOS: brew install wkhtmltopdf

# Generate PDFs
python scripts/generate_pdfs.py
```

Generated PDFs will be placed in `static/documents/pdf/`.

### Available Documents

- **Security Whitepaper** (`docs/whitepapers/security/security-whitepaper.md`)
- **API Reference** (`docs/api/v1/api-reference.md`)
- **User Guide** (`docs/user-guides/getting-started/user-guide.md`)
- **System Architecture** (`docs/technical/architecture/system-architecture.md`)
- **Terms of Service** (`docs/legal/terms-of-service.md`)
- **Privacy Policy** (`docs/legal/privacy-policy.md`)

See [docs/README.md](docs/README.md) for more information.

## Development Status

### Completed
- ✅ Project structure and file organization
- ✅ Landing page and public pages
- ✅ Component library (reusable Jinja2 components)
- ✅ Documentation structure and templates
- ✅ Project reorganization for scalability

### In Progress
- 🚧 User-type based dashboards
- 🚧 Emission calculation engine
- 🚧 Report generation system
- 🚧 Database integration

### Planned
- 📋 Authentication and authorization
- 📋 API implementation
- 📋 Blockchain integration
- 📋 CBAM compliance features

## Notes
- Database integration is stubbed for future use.
- Header/footer are shared via components; page-specific content lives in `templates/pages/`.
- Tailwind is loaded via CDN in templates.

