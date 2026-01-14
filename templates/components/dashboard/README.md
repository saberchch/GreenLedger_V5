# Dashboard Components

Reusable dashboard components for all user types (admin, user, auditor).

## Components

### `sidebar.html`
Left navigation sidebar component.

**Parameters:**
- `nav_items` (list, required): List of navigation items with structure:
  ```python
  {
      'icon': 'material_symbol_name',  # Material Symbol icon name
      'text': 'Display Text',          # Menu item text
      'url': 'route_name',             # Flask route name (optional)
      'active': True/False              # Whether item is active (optional)
  }
  ```
  Use `{'divider': True}` to add a divider between items.

- `plan_info` (dict, optional): Plan usage information:
  ```python
  {
      'plan_name': 'Pro',
      'usage_percent': 75,
      'usage_text': '75% of monthly tokens used'
  }
  ```

- `logo_url` (string, optional): URL for logo image

**Example:**
```jinja2
{% set nav_items = [
    {'icon': 'dashboard', 'text': 'Dashboard', 'url': 'dashboard.user_dashboard', 'active': True},
    {'icon': 'globe', 'text': 'CBAM Module', 'url': 'dashboard.cbam'},
    {'divider': True},
    {'icon': 'settings', 'text': 'Settings', 'url': 'dashboard.settings'}
] %}
{% include 'components/dashboard/sidebar.html' %}
```

### `header.html`
Top header component with page title, actions, and user info.

**Parameters:**
- `page_title` (string, default: 'Dashboard'): Title displayed in header
- `show_new_report_button` (bool, default: True): Show/hide "New Report" button
- `new_report_url` (string, default: '#'): URL/route for new report button
- `new_report_text` (string, default: 'New Report'): Button text
- `show_notifications` (bool, default: True): Show/hide notifications icon
- `notification_count` (int, default: 0): Number of notifications (shows badge if > 0)
- `user_info` (dict, optional): User information:
  ```python
  {
      'name': 'User Name',
      'role': 'User Role',
      'avatar_url': 'URL to avatar image'
  }
  ```

**Example:**
```jinja2
{% set page_title = 'Executive Overview' %}
{% set user_info = {
    'name': 'Sarah Jenkins',
    'role': 'Compliance Lead',
    'avatar_url': 'https://...'
} %}
{% include 'components/dashboard/header.html' %}
```

## Usage

### In Dashboard Pages

1. Extend `layouts/dashboard.html`
2. Set navigation items and other parameters
3. Define `dashboard_content` block with page-specific content

**Example:**
```jinja2
{% extends "layouts/dashboard.html" %}

{% block dashboard_title %}My Dashboard – GreenLedger{% endblock %}

{% set nav_items = [
    {'icon': 'dashboard', 'text': 'Dashboard', 'url': 'dashboard.user_dashboard', 'active': True},
    {'icon': 'settings', 'text': 'Settings', 'url': 'dashboard.settings'}
] %}

{% set page_title = 'My Dashboard' %}

{% block dashboard_content %}
    <!-- Your page content here -->
{% endblock %}
```

## Notes

- The sidebar and header are automatically included by `layouts/dashboard.html`
- Variables set in the page template are available to included components
- Use Flask's `url_for()` for route names in `nav_items`
- The `active` property controls which menu item is highlighted
- All components support dark mode automatically
