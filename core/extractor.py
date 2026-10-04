import re
import os
import urllib.parse
from typing import List, Set, Tuple, Optional
from bs4 import BeautifulSoup
import httpx
from core.models import MediaItem, MediaType, ScrapeResult

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.ico', '.avif'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.m4v'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma', '.opus'}
DOC_EXTENSIONS = {'.pdf', '.zip', '.tar', '.gz', '.7z', '.rar', '.csv', '.json', '.xml'}

TRACKING_DOMAINS = {
    'google-analytics.com', 'googletagmanager.com', 'doubleclick.net', 'facebook.net',
    'facebook.com/tr', 'analytics', 'telemetry', 'stat.sanook.com', 'tracker'
}

DEFAULT_HEADERS = {
    "User-Agent": "MediaHarvester/1.0 (https://github.com/user/media-harvester; contact@example.com) Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive"
}

FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "MediaHarvesterBot/1.0 (https://github.com/user/media-harvester; media-bot@domain.com)",
    "curl/8.7.1",
    "Wget/1.21.4"
]

def is_tracking_url(url: str) -> bool:
    url_lower = url.lower()
    return any(td in url_lower for td in TRACKING_DOMAINS)

def detect_media_type(url: str, tag_name: str = "") -> Tuple[Optional[MediaType], str]:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()
    _, ext = os.path.splitext(path)
    
    # Strip any query trailing from ext if regex missed
    if '?' in ext:
        ext = ext.split('?')[0]
    
    if ext in IMAGE_EXTENSIONS:
        return MediaType.IMAGE, ext
    elif ext in VIDEO_EXTENSIONS:
        return MediaType.VIDEO, ext
    elif ext in AUDIO_EXTENSIONS:
        return MediaType.AUDIO, ext
    elif ext in DOC_EXTENSIONS:
        return MediaType.DOCUMENT, ext
        
    # If tag is strictly an image or video/audio element without extension in path (e.g. dynamic CDN url)
    if any(k in tag_name for k in ['img', 'picture', 'srcset']):
        return MediaType.IMAGE, '.webp' if 'webp' in url.lower() else ('.png' if 'png' in url.lower() else '.jpg')
    elif 'video' in tag_name:
        return MediaType.VIDEO, '.mp4'
    elif 'audio' in tag_name:
        return MediaType.AUDIO, '.mp3'
        
    # Reject other random web pages/scripts
    return None, ""

def extract_best_from_srcset(srcset_val: str, base_url: str) -> Optional[str]:
    if not srcset_val:
        return None
    candidates = []
    entries = srcset_val.split(',')
    for entry in entries:
        parts = entry.strip().split()
        if not parts:
            continue
        url = parts[0].strip()
        score = 1.0
        if len(parts) > 1:
            descriptor = parts[1].lower()
            if descriptor.endswith('w'):
                try:
                    score = float(descriptor[:-1])
                except ValueError:
                    score = 1.0
            elif descriptor.endswith('x'):
                try:
                    score = float(descriptor[:-1]) * 1000
                except ValueError:
                    score = 1.0
        candidates.append((score, url))
    
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_url = candidates[0][1]
    return urllib.parse.urljoin(base_url, best_url)

def clean_media_filename(url: str, default_ext: str = ".jpg") -> str:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    filename = os.path.basename(path)
    if not filename or filename == "/":
        import hashlib
        filename = f"media_{hashlib.md5(url.encode()).hexdigest()[:10]}{default_ext}"
    else:
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        _, ext = os.path.splitext(filename)
        if not ext or len(ext) > 5:
            filename = f"{filename}{default_ext}"
    return filename

def enhance_highres_url(url: str) -> str:
    wp_pattern = r'-\d{2,4}x\d{2,4}(\.[a-zA-Z0-9]+)$'
    if re.search(wp_pattern, url):
        return re.sub(wp_pattern, r'\1', url)
    
    parsed = urllib.parse.urlparse(url)
    if 'unsplash.com' in parsed.netloc:
        query = urllib.parse.parse_qs(parsed.query)
        if 'w' in query:
            query['w'] = ['2560']
        if 'q' in query:
            query['q'] = ['95']
        new_query = urllib.parse.urlencode(query, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))
        
    return url

class MediaExtractor:
    def __init__(self, timeout: float = 15.0, headers: Optional[dict] = None, cookies: Optional[dict] = None):
        self.timeout = timeout
        self.headers = headers or DEFAULT_HEADERS
        self.cookies = cookies or {}
        
    def fetch_html(self, url: str) -> Tuple[str, str, httpx.Response]:
        last_error = None

        # Primary: Chrome-impersonated request (beats TLS-fingerprint blocks)
        try:
            from curl_cffi import requests as imp_requests
            r = imp_requests.get(
                url, impersonate="chrome", cookies=self.cookies,
                allow_redirects=True, timeout=self.timeout,
            )
            r.raise_for_status()
            return str(r.url), r.text, r
        except Exception as e:
            last_error = e

        headers_to_try = [self.headers] + [
            {**self.headers, "User-Agent": ua} for ua in FALLBACK_USER_AGENTS
        ]
        
        for h in headers_to_try:
            try:
                with httpx.Client(headers=h, cookies=self.cookies, follow_redirects=True, timeout=self.timeout) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    final_url = str(response.url)
                    html = response.text
                    return final_url, html, response
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in [403, 401, 429]:
                    continue
                raise e
            except Exception as e:
                last_error = e
                continue
                
        if last_error:
            raise last_error
        raise RuntimeError("Failed to fetch HTML")

    def extract(self, url: str) -> ScrapeResult:
        final_url, html, _ = self.fetch_html(url)
        return self.extract_from_html(html, final_url)

    def extract_from_html(self, html: str, final_url: str) -> ScrapeResult:
        soup = BeautifulSoup(html, 'lxml')
        
        page_title = soup.title.string.strip() if soup.title and soup.title.string else final_url
        seen_urls: Set[str] = set()
        items: List[MediaItem] = []

        def add_item(media_url: str, tag_name: str, alt: str = "", width=None, height=None):
            if not media_url:
                return
            
            full_url = urllib.parse.urljoin(final_url, media_url.strip())
            
            # Skip invalid, data URIs, javascript or tracking beacons
            if full_url.startswith('data:') or full_url.startswith('javascript:'):
                return
            if not full_url.startswith(('http://', 'https://')):
                return
            if is_tracking_url(full_url):
                return
                
            enhanced_url = enhance_highres_url(full_url)
            if enhanced_url in seen_urls:
                return
            
            media_type, ext = detect_media_type(enhanced_url, tag_name)
            if not media_type:
                # Discard non-media assets
                return
                
            seen_urls.add(enhanced_url)
            filename = clean_media_filename(enhanced_url, ext or '.jpg')
            
            item = MediaItem(
                url=enhanced_url,
                media_type=media_type,
                source_tag=tag_name,
                original_filename=filename,
                extension=ext.lower(),
                alt_text=alt,
                width=width,
                height=height,
                source_page_url=final_url
            )
            items.append(item)

        # 1. <img> tags (src, data-src, srcset, etc.)
        for img in soup.find_all('img'):
            alt = img.get('alt', '')
            width = img.get('width')
            height = img.get('height')
            
            srcset = img.get('srcset') or img.get('data-srcset')
            if srcset:
                best_srcset_url = extract_best_from_srcset(srcset, final_url)
                if best_srcset_url:
                    add_item(best_srcset_url, 'img[srcset]', alt, width, height)
            
            for attr in ['data-original', 'data-src', 'data-highres', 'data-zoom-image', 'data-lazy-src', 'data-full', 'data-url', 'src']:
                val = img.get(attr)
                if val:
                    add_item(val, f'img[{attr}]', alt, width, height)
                    break

        # 2. <picture> and <source>
        for source in soup.find_all('source'):
            srcset = source.get('srcset')
            src = source.get('src')
            if srcset:
                best_url = extract_best_from_srcset(srcset, final_url)
                if best_url:
                    add_item(best_url, 'source[srcset]')
            elif src:
                add_item(src, 'source[src]')

        # 3. <video> & <audio>
        for video in soup.find_all('video'):
            src = video.get('src')
            if src:
                add_item(src, 'video')
            poster = video.get('poster')
            if poster:
                add_item(poster, 'video[poster]')

        for audio in soup.find_all('audio'):
            src = audio.get('src')
            if src:
                add_item(src, 'audio')

        # 4. Background images in style attributes
        bg_pattern = re.compile(r'url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)', re.IGNORECASE)
        for tag in soup.find_all(attrs={"style": True}):
            style = tag.get("style", "")
            matches = bg_pattern.findall(style)
            for m in matches:
                add_item(m, 'style[background-image]')

        # 5. Background images in <style> blocks
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                matches = bg_pattern.findall(style_tag.string)
                for m in matches:
                    add_item(m, 'css[background-image]')

        # 6. Links (<a>) pointing strictly to media files
        for a in soup.find_all('a', href=True):
            href = a['href']
            parsed = urllib.parse.urlparse(href)
            _, ext = os.path.splitext(parsed.path.lower())
            if ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS or ext in DOC_EXTENSIONS:
                add_item(href, 'a[href]', alt=a.get_text(strip=True))

        # Calculate statistics
        stats = {}
        for item in items:
            type_name = item.media_type.value
            stats[type_name] = stats.get(type_name, 0) + 1

        return ScrapeResult(
            source_url=final_url,
            title=page_title,
            items=items,
            stats=stats
        )

    def extract_internal_links(self, html: str, base_url: str) -> List[str]:
        """Extract all same-domain internal <a href> links from a page."""
        soup = BeautifulSoup(html, 'lxml')
        base_parsed = urllib.parse.urlparse(base_url)
        links = []
        for a in soup.find_all('a', href=True):
            href = urllib.parse.urljoin(base_url, a['href'].strip())
            parsed = urllib.parse.urlparse(href)
            # Only same domain, no JS; keep query (often identifies the page, e.g. ?episode_no=3)
            if parsed.netloc == base_parsed.netloc and parsed.scheme in ('http', 'https'):
                clean = parsed._replace(fragment='').geturl()
                links.append(clean)
        return list(dict.fromkeys(links))  # deduplicate preserving order

    def extract_recursive(self, start_url: str, depth: int = 1, link_pattern: Optional[str] = None) -> ScrapeResult:
        """
        Recursively crawl same-domain pages up to *depth* levels deep.
        If *link_pattern* is given, only follow links whose URL matches the regex.
        Returns a merged ScrapeResult containing items from all discovered pages.
        """
        visited_pages: Set[str] = set()
        all_items: List[MediaItem] = []
        all_seen_urls: Set[str] = set()
        root_title = start_url

        def crawl(url: str, current_depth: int):
            nonlocal root_title
            if url in visited_pages or current_depth < 0:
                return
            visited_pages.add(url)

            try:
                final_url, html, _ = self.fetch_html(url)
            except Exception:
                return

            result = self.extract_from_html(html, final_url)
            if current_depth == depth:
                root_title = result.title  # title from entry page

            # Merge unique items
            for item in result.items:
                if item.url not in all_seen_urls:
                    all_seen_urls.add(item.url)
                    all_items.append(item)

            # Recurse into linked pages
            if current_depth > 0:
                child_links = self.extract_internal_links(html, final_url)
                if link_pattern:
                    child_links = [l for l in child_links if re.search(link_pattern, l)]
                for link in child_links:
                    crawl(link, current_depth - 1)

        crawl(start_url, depth)

        stats: dict = {}
        for item in all_items:
            stats[item.media_type.value] = stats.get(item.media_type.value, 0) + 1

        return ScrapeResult(
            source_url=start_url,
            title=root_title,
            items=all_items,
            stats=stats
        )
