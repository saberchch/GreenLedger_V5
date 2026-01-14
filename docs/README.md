# GreenLedger Documentation

This directory contains all project documentation, whitepapers, and guides.

## Structure

```
docs/
├── whitepapers/          # Technical and security whitepapers
│   └── security/        # Security-related documentation
├── api/                  # API documentation
│   └── v1/              # API v1 documentation
├── user-guides/          # End-user documentation
│   ├── getting-started/  # Onboarding guides
│   ├── modules/          # Module-specific guides
│   └── dashboards/      # Dashboard usage guides
├── technical/            # Technical documentation
│   ├── architecture/    # System architecture docs
│   ├── deployment/       # Deployment guides
│   └── development/     # Development setup and guidelines
└── legal/                # Legal documents (terms, privacy, etc.)
```

## PDF Documents

PDF versions of documents are stored in `static/documents/pdf/` and can be accessed via the web application.

### Available Documents

- **Security Whitepaper** (`security-whitepaper.pdf`) - Comprehensive security documentation
- **API Documentation** (`api-v1-reference.pdf`) - Complete API reference guide
- **User Guide** (`user-guide.pdf`) - End-user manual
- **Developer Guide** (`developer-guide.pdf`) - Technical development documentation

## Generating PDFs

PDFs can be generated from Markdown sources using:

```bash
# Install dependencies
pip install markdown pdfkit

# Generate PDF from markdown
python scripts/generate_pdfs.py
```

## Document Status

- [ ] Security Whitepaper (Template created)
- [ ] API Documentation (Template created)
- [ ] User Guide (Template created)
- [ ] Developer Guide (Template created)
- [ ] Terms of Service (Template created)
- [ ] Privacy Policy (Template created)
