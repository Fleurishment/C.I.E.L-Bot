import aiohttp
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import re

class FandomScraper:
    BASE_URL = "https://fategrandorder.fandom.com/wiki"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def get_servant_lore(self, servant_name: str) -> Optional[Dict]:
        """Scrape servant lore and background from Fandom"""
        url_name = servant_name.replace(" ", "_").replace("(", "").replace(")", "")
        url = f"{self.BASE_URL}/{url_name}"
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=15, ssl=False) as resp:
                    if resp.status != 200:
                        # Try alternative spelling
                        alt_name = servant_name.replace(" ", "_")
                        alt_url = f"{self.BASE_URL}/{alt_name}"
                        async with session.get(alt_url, timeout=15, ssl=False) as alt_resp:
                            if alt_resp.status != 200:
                                return None
                            html = await alt_resp.text()
                    else:
                        html = await resp.text()
                    
            soup = BeautifulSoup(html, 'html.parser')  # Use html.parser instead of lxml
            data = {}
            
            # Get intro paragraphs
            content = soup.find('div', {'id': 'mw-content-text'})
            if content:
                paragraphs = content.find_all('p', recursive=False)[:3]
                lore_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                data['lore'] = lore_text[:1500] + "..." if len(lore_text) > 1500 else lore_text
            
            # Get servant image
            infobox = soup.find('aside', {'class': 'portable-infobox'})
            if infobox:
                img = infobox.find('img')
                if img:
                    src = img.get('data-src') or img.get('src')
                    if src:
                        data['image_url'] = src
            
            return data if data.get('lore') else None
            
        except Exception as e:
            print(f"Fandom error: {e}")
            return None
    
    async def get_events(self) -> List[Dict]:
        """Get events - fallback to hardcoded recent events if scraping fails"""
        url = f"{self.BASE_URL}/Event_List"
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=15, ssl=False) as resp:
                    if resp.status != 200:
                        return self._get_fallback_events()
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            events = []
            
            tables = soup.find_all('table', {'class': 'wikitable'})
            for table in tables[:2]:
                rows = table.find_all('tr')[1:]
                for row in rows[:5]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        event_name = cols[0].get_text(strip=True)
                        duration = cols[1].get_text(strip=True)
                        events.append({
                            'name': event_name,
                            'duration': duration,
                            'type': 'Event'
                        })
            
            return events if events else self._get_fallback_events()
            
        except Exception as e:
            print(f"Events error: {e}")
            return self._get_fallback_events()
    
    def _get_fallback_events(self):
        """Return recent events when scraping fails"""
        return [
            {'name': 'FGO Festival 2024', 'duration': 'Ongoing', 'type': 'Anniversary'},
            {'name': 'Summer Event 2024', 'duration': 'Upcoming', 'type': 'Seasonal'},
            {'name': 'Check Fandom Wiki for current events', 'duration': 'N/A', 'type': 'Info'}
        ]

class GamePressScraper:
    BASE_URL = "https://grandorder.gamepress.gg"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://grandorder.gamepress.gg/'
        }
    
    async def get_servant_rating(self, servant_name: str) -> Optional[Dict]:
        """Scrape servant tier and ratings"""
        search_name = servant_name.lower().replace(" ", "-").replace("(", "").replace(")", "")
        url = f"{self.BASE_URL}/servant/{search_name}"
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=15, ssl=False) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            data = {}
            
            # Get tier
            tier_div = soup.find('div', string=re.compile('Tier', re.I))
            if tier_div:
                data['tier'] = tier_div.find_parent().get_text(strip=True)
            
            # Get ratings from meta tags or specific divs
            rating_divs = soup.find_all('div', {'class': 'field--name-field-rating'})
            if rating_divs:
                ratings = {}
                for div in rating_divs:
                    label = div.find_previous('div', {'class': 'field__label'})
                    if label:
                        ratings[label.get_text(strip=True)] = div.get_text(strip=True)
                data['ratings'] = ratings
            
            return data if data else None
            
        except Exception as e:
            print(f"GamePress error: {e}")
            return None
    
    async def get_tier_list(self) -> List[Dict]:
        """Get tier list - often blocked, return fallback"""
        # GamePress tier list is heavily protected, use fallback
        return [
            {'tier': 'S', 'servants': ['Arjuna (Alter)', 'Koyanskaya of Light', 'Oberon']},
            {'tier': 'A+', 'servants': ['Artoria Caster', 'Tamamo (Caster)', 'Merlin']},
            {'tier': 'A', 'servants': ['Gilgamesh', 'Kama', 'Musashi']}
        ]
    
    async def get_farming_guide(self, material: str) -> Optional[Dict]:
        url = f"{self.BASE_URL}/farming-guide"
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=15, ssl=False) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            # Simplified parsing
            return {
                'material': material,
                'locations': ['Check gamepress.gg for detailed farming info']
            }
        except:
            return None
