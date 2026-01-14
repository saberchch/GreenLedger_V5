# GreenLedger V5 Project Structure

This document describes the reorganized project structure designed for scalability and maintainability.

## Directory Structure

```
GreenLedger_V5/
├── app/                          # Main application package
│   ├── core/                     # Core application components
│   │   ├── auth/                 # Authentication & authorization
│   │   ├── config/               # Configuration management
│   │   ├── extensions/           # Flask extensions initialization
│   │   └── utils/                # Core utilities (enums, validators, permissions)
│   │
│   ├── features/                 # Feature modules (business logic)
│   │   ├── emissions/            # Emission calculation engine
│   │   │   ├── calculators.py    # Calculation algorithms
│   │   │   ├── services.py       # Business logic services
│   │   │   └── routes.py         # Feature-specific routes
│   │   ├── cbam/                 # CBAM compliance module
│   │   ├── reports/              # Report generation
│   │   ├── data_collection/      # Data input & management
│   │   └── explorer/             # Public explorer feature
│   │
│   ├── dashboards/               # User-type specific dashboards
│   │   ├── admin/                # Administrator dashboard
│   │   ├── user/                 # Standard user dashboard
│   │   └── auditor/              # Auditor/verifier dashboard
│   │
│   ├── shared/                   # Shared components
│   │   ├── decorators/           # Custom decorators
│   │   ├── middleware/           # Request/response middleware
│   │   └── exceptions/           # Custom exception classes
│   │
│   ├── api/                      # REST API layer
│   │   └── v1/                   # API version 1
│   │       ├── activities.py
│   │       ├── emissions.py
│   │       └── reports.py
│   │
│   ├── models/                   # Database models
│   │   ├── activity.py
│   │   ├── company.py
│   │   ├── emission_factor.py
│   │   ├── facility.py
│   │   └── report.py
│   │
│   ├── main.py                   # Public routes (landing, modules, etc.)
│   ├── factory.py                # Application factory
│   └── extensions.py             # Flask extensions (legacy - move to core/extensions)
│
├── templates/                     # Jinja2 templates
│   ├── layouts/                  # Base layouts
│   ├── components/               # Reusable components
│   └── pages/                    # Page templates
│
├── static/                        # Static assets
│   ├── css/
│   ├── js/
│   ├── images/
│   └── documents/                # PDF documents
│       └── pdf/
│
├── docs/                          # Documentation
│   ├── whitepapers/              # Technical whitepapers
│   ├── api/                      # API documentation
│   ├── user-guides/              # User documentation
│   ├── technical/                # Technical documentation
│   └── legal/                    # Legal documents
│
├── tests/                         # Test suite
│
├── scripts/                       # Utility scripts
│   └── generate_pdfs.py          # PDF generation script
│
├── migrations/                    # Database migrations
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── docker-compose.yml            # Docker Compose configuration
├── run.py                        # Application entry point
├── setup.sh                      # Setup script
├── README.md                     # Main README
└── PROJECT_STRUCTURE.md          # This file
```

## Architecture Principles

### 1. Feature-Based Organization
Each feature module (`app/features/*`) is self-contained with:
- Routes (if feature-specific)
- Services (business logic)
- Models (if feature-specific)
- Templates (if feature-specific)

### 2. Separation of Concerns
- **Core**: Shared functionality, configuration, base classes
- **Features**: Business logic modules
- **Dashboards**: User interface for different user types
- **API**: REST API layer
- **Shared**: Cross-cutting concerns (decorators, middleware, exceptions)

### 3. Scalability
- Easy to add new features without affecting existing code
- Clear boundaries between modules
- Shared utilities prevent code duplication

## Migration Plan

### Phase 1: Core Reorganization
- [ ] Move `app/config.py` → `app/core/config/`
- [ ] Move `app/extensions.py` → `app/core/extensions/`
- [ ] Move `app/utils/` → `app/core/utils/`
- [ ] Move `app/auth/` → `app/core/auth/`

### Phase 2: Feature Organization
- [ ] Organize `app/emissions/` → `app/features/emissions/`
- [ ] Organize `app/cbam/` → `app/features/cbam/`
- [ ] Organize `app/reports/` → `app/features/reports/`
- [ ] Organize `app/data_collection/` → `app/features/data_collection/`

### Phase 3: Dashboard Organization
- [ ] Create `app/dashboards/user/` for standard user dashboard
- [ ] Create `app/dashboards/admin/` for admin dashboard
- [ ] Create `app/dashboards/auditor/` for auditor dashboard
- [ ] Move `app/dashboard/` → `app/dashboards/user/`

### Phase 4: Shared Components
- [ ] Create shared decorators
- [ ] Create shared middleware
- [ ] Create custom exceptions

## Next Steps

1. **Complete Migration**: Move existing files to new structure
2. **Update Imports**: Update all import statements
3. **Update Factory**: Update `app/factory.py` to use new structure
4. **Testing**: Ensure all routes and functionality work
5. **Documentation**: Update API docs and README

## Notes

- Keep backward compatibility during migration
- Update tests to reflect new structure
- Update CI/CD pipelines if needed
- Document breaking changes
