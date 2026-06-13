#!/usr/bin/env python3
"""
Script to fetch Albanian news RSS feeds and save as JSON.
Runs via GitHub Actions every hour.
"""
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import ssl

# Disable SSL verification for problematic sites
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

RSS_FEEDS = [
    {"name": "Panorama", "url": "https://www.panorama.al/feed/", "category": "politike"},
    {"name": "Shqiptarja", "url": "https://www.shqiptarja.com/feed/", "category": "politike"},
    {"name": "Gazeta Express", "url": "https://www.gazetaexpress.com/feed/", "category": "politike"},
    {"name": "Balkanweb", "url": "https://www.balkanweb.com/site/feed/", "category": "politike"},
    {"name": "Gazeta Blic", "url": "https://gazetablic.com/feed/", "category": "kronike"},
    {"name": "ABC News", "url": "https://abcnews.al/feed/", "category": "politike"},
    {"name": "Gazeta Mapo", "url": "https://gazetamapo.al/feed/", "category": "politike"},
    {"name": "Shekulli", "url": "https://shekulli.com.al/feed/", "category": "politike"},
    {"name": "Lajmi i Fundit", "url": "https://lajmifundit.al/feed/", "category": "kronike"},
    {"name": "Lajme.al", "url": "https://www.lajme.al/feed/", "category": "politike"},
    {"name": "Scan TV", "url": "https://www.scan-tv.com/feed/", "category": "ekonomi"},
    {"name": "Gazeta Tema", "url": "https://www.gazetatema.net/web/feed/", "category": "politike"},
    {"name": "24 ORE", "url": "https://24-ore.com/?feed=rss2", "category": "politike"},
    {"name": "TV Klan", "url": "https://tvklan.al/feed/", "category": "sport"}
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def clean_html(raw):
    """Remove HTML tags"""
    import re
    clean = re.sub(r'<[^>]+>', '', raw)
    return clean.strip()

def parse_date(date_str):
    """Parse various date formats"""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%d %b %Y %H:%M:%S %z',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            continue
    try:
        # Try without timezone
        return datetime.strptime(date_str.strip()[:19], '%Y-%m-%dT%H:%M:%S')
    except:
        pass
    return datetime.now(timezone.utc)

def fetch_feed(feed):
    """Fetch and parse a single RSS feed"""
    news_items = []
    try:
        req = urllib.request.Request(feed['url'], headers=HEADERS)
        response = urllib.request.urlopen(req, timeout=15, context=ssl_context)
        data = response.read()

        # Try UTF-8 first, then fallback
        try:
            text = data.decode('utf-8')
        except:
            try:
                text = data.decode('iso-8859-1')
            except:
                text = data.decode('utf-8', errors='ignore')

        # Parse XML
        root = ET.fromstring(text)

        # Handle RSS 2.0
        items = root.findall('.//item')
        if not items:
            # Handle Atom
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('.//atom:entry', ns)
            if not entries:
                entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')

            for idx, entry in enumerate(entries[:15]):
                title_el = entry.find('atom:title', ns) or entry.find('.//{http://www.w3.org/2005/Atom}title')
                link_el = entry.find('atom:link', ns) or entry.find('.//{http://www.w3.org/2005/Atom}link')
                summary_el = entry.find('atom:summary', ns) or entry.find('.//{http://www.w3.org/2005/Atom}summary')
                content_el = entry.find('atom:content', ns) or entry.find('.//{http://www.w3.org/2005/Atom}content')
                updated_el = entry.find('atom:updated', ns) or entry.find('.//{http://www.w3.org/2005/Atom}updated')
                published_el = entry.find('atom:published', ns) or entry.find('.//{http://www.w3.org/2005/Atom}published')

                title = title_el.text if title_el is not None else ''
                link = ''
                if link_el is not None:
                    link = link_el.get('href', '') or link_el.text or ''

                desc = ''
                if summary_el is not None and summary_el.text:
                    desc = summary_el.text
                elif content_el is not None and content_el.text:
                    desc = content_el.text

                pub_date = ''
                if updated_el is not None and updated_el.text:
                    pub_date = updated_el.text
                elif published_el is not None and published_el.text:
                    pub_date = published_el.text

                date = parse_date(pub_date)
                now = datetime.now(timezone.utc)
                diff_hours = (now - date.replace(tzinfo=timezone.utc)).total_seconds() / 3600

                news_items.append({
                    'title': title.strip(),
                    'link': link.strip(),
                    'description': clean_html(desc)[:300],
                    'source': feed['name'],
                    'category': feed['category'],
                    'date': date.isoformat(),
                    'dateStr': date.strftime('%d %b, %H:%M'),
                    'isNew': diff_hours < 24,
                    'id': f"{feed['name'][:3].lower()}{idx}{int(date.timestamp())}"
                })
        else:
            for idx, item in enumerate(items[:15]):
                title_el = item.find('title')
                link_el = item.find('link')
                desc_el = item.find('description')
                pub_date_el = item.find('pubDate')

                title = title_el.text if title_el is not None else ''
                link = link_el.text if link_el is not None else ''
                desc = desc_el.text if desc_el is not None else ''
                pub_date = pub_date_el.text if pub_date_el is not None else ''

                date = parse_date(pub_date)
                now = datetime.now(timezone.utc)
                diff_hours = (now - date.replace(tzinfo=timezone.utc)).total_seconds() / 3600

                news_items.append({
                    'title': title.strip(),
                    'link': link.strip(),
                    'description': clean_html(desc)[:300],
                    'source': feed['name'],
                    'category': feed['category'],
                    'date': date.isoformat(),
                    'dateStr': date.strftime('%d %b, %H:%M'),
                    'isNew': diff_hours < 24,
                    'id': f"{feed['name'][:3].lower()}{idx}{int(date.timestamp())}"
                })

        print(f"✅ {feed['name']}: {len(news_items)} lajme")
        return news_items

    except Exception as e:
        print(f"❌ {feed['name']}: {type(e).__name__}: {str(e)[:80]}")
        return []

def main():
    all_news = []
    success_count = 0

    for feed in RSS_FEEDS:
        items = fetch_feed(feed)
        if items:
            all_news.extend(items)
            success_count += 1

    # Sort by date descending
    all_news.sort(key=lambda x: x['date'], reverse=True)

    output = {
        'lastUpdated': datetime.now(timezone.utc).isoformat(),
        'totalSources': success_count,
        'totalNews': len(all_news),
        'news': all_news
    }

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Total: {len(all_news)} lajme nga {success_count} burime")
    print(f"💾 Ruajtur në news.json")

if __name__ == '__main__':
    main()
