# tools/test_pdf_playwright.py
"""
Sanity test for Playwright PDF generation.
Run: python tools/test_pdf_playwright.py
"""
from playwright.sync_api import sync_playwright

HTML = "<html><body><h1>Playwright PDF test</h1><p>Hello PDF</p></body></html>"

def run_test():
    print("Starting Playwright PDF test...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content(HTML)
        page.pdf(path="playwright_test.pdf", format="A4")
        browser.close()
    print("✓ Created playwright_test.pdf")
    print("Open the file to verify PDF generation works correctly.")

if __name__ == "__main__":
    run_test()
