"""
OSRS Wiki Scraper
Downloads and extracts content from the Old School RuneScape wiki.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OSRSWikiScraper:
    """Scraper for OSRS wiki content."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize scraper with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.base_url = self.config['wiki']['base_url']
        self.output_dir = Path(self.config['wiki']['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.scraped_urls = set()
        self.pages_data = []
        
    def get_wiki_api_url(self, **params) -> str:
        """Construct MediaWiki API URL."""
        api_url = urljoin(self.base_url, "/api.php")
        # URL encode parameter values
        from urllib.parse import urlencode
        params['format'] = 'json'
        return f"{api_url}?{urlencode(params)}"
    
    def get_category_pages(self, category: str, limit: int = 500) -> List[str]:
        """Get all pages in a category."""
        pages = []
        cmcontinue = None
        
        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{category}",
                "cmlimit": "500"
            }
            
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            
            url = self.get_wiki_api_url(**params)
            
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'query' in data and 'categorymembers' in data['query']:
                    for member in data['query']['categorymembers']:
                        pages.append(member['title'])
                
                if 'continue' in data and 'cmcontinue' in data['continue']:
                    cmcontinue = data['continue']['cmcontinue']
                else:
                    break
                    
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error fetching category {category}: {e}")
                break
        
        return pages[:limit]
    
    def get_all_pages(self) -> List[str]:
        """Get all pages from configured categories."""
        all_pages = set()
        categories = self.config['wiki'].get('categories', [])
        
        for category in categories:
            logger.info(f"Fetching pages from category: {category}")
            pages = self.get_category_pages(category)
            all_pages.update(pages)
            logger.info(f"Found {len(pages)} pages in {category}")
            time.sleep(1)
        
        # Also get some popular pages
        logger.info("Fetching additional popular pages...")
        popular_pages = [
            "Main Page",
            "Grand Exchange",
            "Combat",
            "Equipment",
            "Achievement Diary",
            "Minigame",
            "Boss",
            "Slayer",
            "Prayer",
            "Magic"
        ]
        all_pages.update(popular_pages)
        
        max_pages = self.config['wiki'].get('max_pages')
        if max_pages:
            all_pages = list(all_pages)[:max_pages]
        
        return list(all_pages)
    
    def extract_text_content(self, soup: BeautifulSoup) -> Dict[str, any]:
        """Extract structured content from a wiki page."""
        content = {
            'title': '',
            'text': '',
            'infobox': {},
            'tables': [],
            'lists': [],
            'sections': {}
        }
        
        # Get title
        title_elem = soup.find('h1', class_='firstHeading')
        if title_elem:
            content['title'] = title_elem.get_text(strip=True)
        
        # Get main content area
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return content
        
        # Extract infobox (item/quest stats, etc.)
        infobox = content_div.find('table', class_='infobox')
        if infobox:
            content['infobox'] = self._extract_infobox(infobox)
        
        # Extract sections
        current_section = 'Introduction'
        current_text = []
        
        for elem in content_div.find_all(['h2', 'h3', 'p', 'ul', 'ol', 'table', 'dl']):
            if elem.name in ['h2', 'h3']:
                # Save previous section
                if current_text:
                    content['sections'][current_section] = ' '.join(current_text)
                    current_text = []
                current_section = elem.get_text(strip=True)
            
            elif elem.name == 'table' and 'infobox' not in elem.get('class', []):
                # Extract table data
                table_data = self._extract_table(elem)
                if table_data:
                    content['tables'].append({
                        'section': current_section,
                        'data': table_data
                    })
            
            elif elem.name in ['ul', 'ol']:
                # Extract list
                list_items = [li.get_text(strip=True) for li in elem.find_all('li')]
                if list_items:
                    content['lists'].append({
                        'section': current_section,
                        'items': list_items
                    })
            
            else:
                # Regular text
                text = elem.get_text(separator=' ', strip=True)
                if text and len(text) > 20:  # Filter out very short text
                    current_text.append(text)
        
        # Save last section
        if current_text:
            content['sections'][current_section] = ' '.join(current_text)
        
        # Combine all text
        all_text_parts = [content['title']]
        
        # Add infobox as structured text
        if content['infobox']:
            infobox_text = f"Stats/Info: {json.dumps(content['infobox'], indent=2)}"
            all_text_parts.append(infobox_text)
        
        # Add sections
        for section, text in content['sections'].items():
            all_text_parts.append(f"{section}: {text}")
        
        # Add tables
        for table in content['tables']:
            table_text = f"Table ({table['section']}): {json.dumps(table['data'], indent=2)}"
            all_text_parts.append(table_text)
        
        # Add lists
        for lst in content['lists']:
            list_text = f"List ({lst['section']}): {'; '.join(lst['items'])}"
            all_text_parts.append(list_text)
        
        content['text'] = '\n\n'.join(all_text_parts)
        
        return content
    
    def _extract_infobox(self, infobox_table) -> Dict:
        """Extract data from infobox table."""
        data = {}
        rows = infobox_table.find_all('tr')
        
        for row in rows:
            header = row.find('th')
            value = row.find('td')
            
            if header and value:
                key = header.get_text(strip=True)
                val = value.get_text(strip=True)
                if key and val:
                    data[key] = val
        
        return data
    
    def _extract_table(self, table) -> List[Dict]:
        """Extract data from a regular table."""
        data = []
        rows = table.find_all('tr')
        
        if not rows:
            return data
        
        # Get headers
        headers = []
        header_row = rows[0]
        for th in header_row.find_all(['th', 'td']):
            headers.append(th.get_text(strip=True))
        
        if not headers:
            return data
        
        # Get data rows
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) == len(headers):
                row_data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row_data[headers[i]] = cell.get_text(strip=True)
                data.append(row_data)
        
        return data
    
    def scrape_page(self, page_title: str) -> Optional[Dict]:
        """Scrape a single wiki page."""
        if page_title in self.scraped_urls:
            return None
        
        # Use MediaWiki API to get page content
        api_url = self.get_wiki_api_url(
            action="query",
            titles=page_title.replace(' ', '_'),
            prop="extracts|info",
            explaintext="1",
            exintro="0",
            exsectionformat="plain"
        )
        
        try:
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'query' not in data or 'pages' not in data['query']:
                return None
            
            pages = data['query']['pages']
            if not pages:
                return None
            
            page_id = list(pages.keys())[0]
            page_data = pages[page_id]
            
            if 'missing' in page_data:
                return None
            
            # Also get HTML for better parsing
            html_url = urljoin(self.base_url, f"/index.php?title={page_title.replace(' ', '_')}")
            html_response = self.session.get(html_url, timeout=10)
            html_response.raise_for_status()
            soup = BeautifulSoup(html_response.content, 'lxml')
            
            content = self.extract_text_content(soup)
            content['url'] = html_url
            content['page_id'] = page_id
            
            # Add API extract if available
            if 'extract' in page_data:
                content['api_extract'] = page_data['extract']
            
            self.scraped_urls.add(page_title)
            return content
            
        except Exception as e:
            logger.error(f"Error scraping page {page_title}: {e}")
            return None
    
    def save_page_data(self, page_data: Dict, output_file: Path):
        """Save page data to JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)
    
    def run(self):
        """Main scraping function."""
        logger.info("Starting OSRS wiki scraping...")
        
        # Get all pages to scrape
        pages = self.get_all_pages()
        logger.info(f"Found {len(pages)} pages to scrape")
        
        # Scrape pages
        for i, page_title in enumerate(tqdm(pages, desc="Scraping pages")):
            page_data = self.scrape_page(page_title)
            
            if page_data:
                # Save individual page
                safe_title = page_title.replace('/', '_').replace('\\', '_')
                output_file = self.output_dir / f"{safe_title}.json"
                self.save_page_data(page_data, output_file)
                
                self.pages_data.append(page_data)
            
            # Rate limiting
            time.sleep(0.3)
            
            # Save progress periodically
            if (i + 1) % 50 == 0:
                self.save_all_data()
        
        # Final save
        self.save_all_data()
        logger.info(f"Scraping complete! Scraped {len(self.pages_data)} pages.")
    
    def save_all_data(self):
        """Save all scraped data to a single JSON file."""
        output_file = self.output_dir / "all_pages.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.pages_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    scraper = OSRSWikiScraper()
    scraper.run()
