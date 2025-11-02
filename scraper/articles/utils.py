from typing import Any, Dict, Optional
from .models import Article
import logging


logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> Optional[str]:
    """Return cleaned text for a value or None.
    """
    if value is None:
        return None
    try:
        if hasattr(value, 'get_text'):
            text = value.get_text(strip=True)
        else:
            text = str(value).strip()
    except Exception:
        return None
    return text or None


def title_finder(soup) -> Optional[str]:
    """Find an article title inside the parsed HTML.

    Tries these locations in order: <h1>, meta[property="og:title"], <title>.
    Returns cleaned text or None.
    """
    if soup is None:
        return None
    h1 = soup.find('h1')
    if h1:
        logger.debug('Found title in <h1>')
        return _normalize_text(h1)
    og = soup.find('meta', property='og:title')
    if og and og.get('content'):
        logger.debug('Found title in og:title')
        return og.get('content').strip()
    title_tag = soup.find('title')
    if title_tag:
        logger.debug('Found title in <title>')
        return _normalize_text(title_tag)
    logger.debug('Title not found')
    return None


def body_finder(soup):
    """Locate the main article body tag.

    Tries a number of common selectors and falls back to the largest <div>
    by text length when reasonable.
    Returns the Tag or None.
    """
    if soup is None:
        return None
    selectors = [
        ('div', {'class': 'table-post'}),
        ('article', {}),
        ('div', {'class': 'article-body'}),
        ('div', {'class': 'post-content'}),
    ]
    # deleting divs with ads 
    for ad_div in soup.find_all('div', {'class': 'ad-container'}):
        ad_div.decompose()
    for name, attrs in selectors:
        tag = soup.find(name, attrs)
        if tag:
            logger.debug('Found body with selector %s %s', name, attrs)
            return tag
    divs = soup.find_all('div')
    if not divs:
        logger.debug('No <div> elements found for body')
        return None
    best = max(divs, key=lambda d: len(d.get_text(strip=True) or ''))
    if len(best.get_text(strip=True) or '') > 100:
        logger.debug('Choosing largest <div> as body')
        return best
    logger.debug('Body not found')
    return None


def published_at_finder(soup) -> Optional[str]:
    """Try to find and normalize a published date.

    Returns a string formatted as 'DD.MM.YYYY HH:MM:SS' or None.
    """
    if soup is None:
        return None
    try:
        import dateparser
        import datetime
    except Exception:
        logger.debug('dateparser not available; skipping published_at parsing')
        return None

    time_tag = soup.find('time')
    if time_tag:
        raw = time_tag.get('datetime') or time_tag.get_text(strip=True)
        if raw:
            parsed = dateparser.parse(raw, languages=['pl'])
            if parsed:
                return parsed.strftime('%d.%m.%Y %H:%M:%S')

    try:
        import re
        author_link = soup.find('a', href=re.compile(r'^/autorzy/'))
        if author_link:
            possible = author_link.find_next('p').text
            if possible:
                parsed = dateparser.parse(possible, languages=['pl'])
                if parsed:
                    return parsed.strftime('%d.%m.%Y %H:%M:%S')
    except Exception:
        logger.debug('published date parsing failed', exc_info=True)

    logger.debug('Published date not found')
    return None


def webdriver_builder():
    """Create a headless Chrome webdriver and return it.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def save_article(article: Dict[str, Any]):
    """Save an article dictionary to the DB
    """
    import uuid
    import datetime
    from django.utils import timezone

    title = _normalize_text(article.get('title')) or 'Not Found'

    body_val = article.get('body')
    if hasattr(body_val, 'get_text'):
        body_html = str(body_val)
        plain_body = _normalize_text(body_val.get_text(strip=True)) or 'Not Found'
    else:
        body_html = _normalize_text(body_val) or 'Not Found'
        plain_body = _normalize_text(article.get('plain_body')) or (body_html if body_html != 'Not Found' else 'Not Found')

    url = article.get('url') or f'not-found-{uuid.uuid4()}'

    published_at_val = article.get('published_at')
    published_at = None
    if published_at_val:
        try:
            if isinstance(published_at_val, datetime.datetime):
                published_at = published_at_val
            else:
                published_at = datetime.datetime.strptime(published_at_val, '%d.%m.%Y %H:%M:%S')
        except Exception:
            published_at = None

    defaults = {
        'title': title,
        'body': body_html,
        'plain_body': plain_body,
    }
    if published_at:
        tz = timezone.get_current_timezone()
        published_at = timezone.make_aware(published_at, tz)
        defaults['published_at'] = published_at


    obj, created = Article.objects.update_or_create(url=url, defaults=defaults)
    if created:
        logger.info('Saved new article: %s (url=%s)', obj.title, obj.url)
    else:
        # if somehow previous check let through URL that is already in DB
        logger.info('Updated article: %s (url=%s)', obj.title, obj.url)
    return obj


def scraper_run(websites_path: str = 'websites.json') -> None:
    """Main scraping loop.

    Loads URLs from a JSON file and scrapes each page using Selenium
    Selenium is used so javascript frameworks on websites will not be a problem
    """
    from bs4 import BeautifulSoup
    import requests
    import json
    from selenium.webdriver.support.wait import WebDriverWait
    from urllib.parse import urlparse
    import sys

    skipped_cnt = 0

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0'
        ),
    }

    driver = None
    try:
        logger.info('Initializing webdriver...')
        driver = webdriver_builder()

        with open(websites_path, 'r', encoding='utf-8') as fh:
            links = json.load(fh)

        bad_statuses = {404, 500, 408, 403}
        for idx, link in enumerate(list(links), start=1):
            if link.endswith('/'):
                # clears "/" from passed URL to protect from duplicates, uses more modern method if python version is 3.9+
                if sys.version_info >= (3, 9):
                    link = link.removesuffix('/')
                else:
                    link = link[:-1]
            try:
                if Article.objects.filter(url=link).exists():
                    logger.info('Skipping already-saved URL: %s', link)
                    skipped_cnt =+ 1
                    continue
            except Exception:
                logger.debug('Could not check DB for existing article', exc_info=True)
            try:
                parsed = urlparse(link or '')
                if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                    logger.warning('Skipping invalid URL: %s', link)
                    skipped_cnt =+ 1
                    continue
                r = requests.get(link, timeout=10, headers=headers)

            except requests.exceptions.RequestException as exc:
                logger.warning('Request error for %s: %s', link, exc)
                skipped_cnt =+ 1
                continue
            if r.status_code in bad_statuses:
                logger.warning('Bad status %s for %s', r.status_code, link)
                skipped_cnt =+ 1
                continue

            logger.info('Scraping (%d/%d): %s | Skipped links: %d', idx, len(links), link, skipped_cnt)
            try:
                driver.get(link)
                WebDriverWait(driver, 2) # 2 seconds for javascript to load
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')

                article = {
                    'title': title_finder(soup),
                    'body': body_finder(soup),
                    'plain_body': None,
                    'published_at': published_at_finder(soup),
                    'url': link,
                }
                if article['body'] is not None and hasattr(article['body'], 'get_text'):
                    article['plain_body'] = article['body'].get_text(strip=True)
                else:
                    article['plain_body'] = _normalize_text(article.get('plain_body'))

                save_article(article)
            except Exception as exc:
                logger.exception('Failed to scrape %s: %s', link, exc)
                continue
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                logger.debug('Error quitting webdriver', exc_info=True)