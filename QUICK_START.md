# Quick Start Guide

# Quick Start Guide

## Setup Database

```bash
source venv/bin/activate
# Reset database and seed with mock data
python scripts/reset_db_and_seed.py
```

## Run Application

```bash
source venv/bin/activate
python run.py
```

Visit: `http://localhost:5000`

## Login Credentials

**Admin User:**
- Email: `admin@acme.com`
- Password: `admin123`

**Other Users:**
See `README.md` for complete list.

## Troubleshooting

### "FLASK_APP not found"
```bash
export FLASK_APP=run.py
# Or use the .flaskenv file (already created)
```

### "Migrations directory exists"
```bash
# Remove and reinitialize
rm -rf migrations
flask db init
```

### "Module not found"
```bash
# Make sure venv is activated
source venv/bin/activate
pip install -r requirements.txt
```

