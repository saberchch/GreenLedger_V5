#!/usr/bin/env python3
"""
Script to generate PDFs from Markdown documentation files.
Requires: markdown, pdfkit, and wkhtmltopdf
"""

import os
import sys
from pathlib import Path

try:
    import markdown
    import pdfkit
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install markdown pdfkit")
    sys.exit(1)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "docs"
OUTPUT_DIR = BASE_DIR / "static" / "documents" / "pdf"

# PDF generation mapping
PDF_MAPPINGS = {
    "security-whitepaper.pdf": DOCS_DIR / "whitepapers" / "security" / "security-whitepaper.md",
    "api-v1-reference.pdf": DOCS_DIR / "api" / "v1" / "api-reference.md",
    "user-guide.pdf": DOCS_DIR / "user-guides" / "getting-started" / "user-guide.md",
    "developer-guide.pdf": DOCS_DIR / "technical" / "architecture" / "system-architecture.md",
    "terms-of-service.pdf": DOCS_DIR / "legal" / "terms-of-service.md",
    "privacy-policy.pdf": DOCS_DIR / "legal" / "privacy-policy.md",
}

# CSS for PDF styling
PDF_CSS = """
<style>
    body {
        font-family: 'Public Sans', Arial, sans-serif;
        line-height: 1.6;
        color: #111814;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    h1 {
        color: #13ec80;
        border-bottom: 2px solid #13ec80;
        padding-bottom: 10px;
    }
    h2 {
        color: #618975;
        margin-top: 30px;
    }
    code {
        background-color: #f6f8f7;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
    }
    pre {
        background-color: #f6f8f7;
        padding: 15px;
        border-radius: 5px;
        overflow-x: auto;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
    }
    th, td {
        border: 1px solid #dbe6e0;
        padding: 10px;
        text-align: left;
    }
    th {
        background-color: #13ec80;
        color: #111814;
    }
</style>
"""


def markdown_to_html(md_file: Path) -> str:
    """Convert Markdown file to HTML."""
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'tables']
    )
    
    return f"<html><head>{PDF_CSS}</head><body>{html}</body></html>"


def generate_pdf(md_file: Path, output_file: Path):
    """Generate PDF from Markdown file."""
    if not md_file.exists():
        print(f"Warning: {md_file} not found. Skipping.")
        return False
    
    try:
        html_content = markdown_to_html(md_file)
        
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
        }
        
        pdfkit.from_string(html_content, str(output_file), options=options)
        print(f"✓ Generated: {output_file.name}")
        return True
    except Exception as e:
        print(f"✗ Error generating {output_file.name}: {e}")
        return False


def main():
    """Main function to generate all PDFs."""
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Generating PDFs from Markdown documentation...\n")
    
    success_count = 0
    total_count = len(PDF_MAPPINGS)
    
    for pdf_name, md_file in PDF_MAPPINGS.items():
        output_file = OUTPUT_DIR / pdf_name
        if generate_pdf(md_file, output_file):
            success_count += 1
    
    print(f"\nCompleted: {success_count}/{total_count} PDFs generated.")
    
    if success_count < total_count:
        print("\nNote: Some PDFs could not be generated.")
        print("Make sure wkhtmltopdf is installed:")
        print("  Ubuntu/Debian: sudo apt-get install wkhtmltopdf")
        print("  macOS: brew install wkhtmltopdf")


if __name__ == "__main__":
    main()
