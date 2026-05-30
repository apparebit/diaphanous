#!.venv/bin/python

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright, Page

#     # Determine deck size
#     deck_size = page.evaluate(
#         'JSON.parse(readerViewDataFromServer.MANIFEST_BODY).pages.length'
#     )
#     # Determine base URL for slides
#     link = page.locator('iframe[name=targetFrame]').get_attribute('src')
#     query = parse_qs(urlparse(link).query)
#     base, _, _ = (query["basepath"][0] + query["relativepath"][0]).rpartition("/")
#     print(f'  ⦿ base="{base}"')

def digital2023():
    for index in range(1, 286):
        yield (
            "https://indd.adobe.com/content/2/"
            "672a3366-328d-4a51-98a5-95c1082618d2/1674650530560/package/1/"
            f"publication-{index}.html"
        )


def digital2024():
    for index in range(1, 289):
        yield (
            "https://indd.adobe.com/content/2/"
            "eede3550-b3a7-4ebf-b417-3258cb4f15dc/3416970665860/package/82zp/"
            f"publication-{index}.html"
        )


def digital2025():
    for index in range(1, 287):
        yield (
            "https://indd.adobe.com/content/2/"
            "846e6c08-8bce-4853-b2c6-2e0e33b2e213/3480934980441/package/7qep/"
            f"publication-{index}.html"
        )


def digital2026():
    for index in range(1, 2):
        yield (
            "https://indd.adobe.com/content/2/"
            "323049c9-a7a9-4f43-89ff-28f2cadf3820/3522078272650/package/b5ky/"
            f"publication-{index}.html"
        )


def get_deck_metadata(url: str) -> None:
    with browser_page() as page:
        page.goto(url)

        # Determine deck size
        slides = page.evaluate(
            'JSON.parse(readerViewDataFromServer.MANIFEST_BODY).pages.length'
        )

        # Determine base URL for slides
        link = page.locator('iframe[name=targetFrame]').get_attribute('src')
        query = parse_qs(urlparse(link).query) # type: ignore
        base, _, _ = (
            query["basepath"][0] + query["relativepath"][0] # type: ignore
        ).rpartition("/") # type: ignore

    print(f"Location : {base}")
    print(f'Slides   : {slides}')


def capture_slide(page: Page, url: str, path: str) -> None:
    print(f'capture "{url}"')
    page.goto(url)
    page.pdf(
        path=path,
        width="1080px",
        height="1920px",
        landscape=True,
        print_background=True,
    )


def capture_deck(name: str, urls: Iterable[str]) -> None:
    with browser_page() as page:
        for index, url in enumerate(urls):
            capture_slide(page, url, f"{name}/slide-{index+1:03}.pdf")


@contextmanager
def browser_page() -> Iterator[Page]:
    with sync_playwright() as playwright:
        # Scrape in the open: Use Chrome and the correct user agent.
        # Also, no stealth measures.
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=False,
        )

        context = browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
            ),
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
            is_mobile=False,
        )

        page = context.new_page()

        try:
            yield page
        finally:
            browser.close()


#get_deck_metadata("https://datareportal.com/reports/digital-2026-local-country-headlines")

#capture_deck("digital2023", digital2023())
#capture_deck("digital2024", digital2024())
#capture_deck("digital2025", digital2025())
capture_deck("digital2026", digital2026())

# When done: pdfunite slide-*.pdf digital202x.pdf
