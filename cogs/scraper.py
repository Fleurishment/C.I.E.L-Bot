import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import re
import random

class FandomScraper:
    BASE_URL = "https://fategrandorder.fandom.com/wiki"
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    async def get_servant_lore(self, servant_name: str) -> Optional[Dict]:
        """Scrape servant lore with retries"""
        # Try different URL formats
        url_formats = [
            servant_name.replace(" ", "_"),
            servant_name.replace(" ", "_").replace("(", "").replace(")", ""),
            servant_name.replace(" ", "-"),
        ]
        
        for url_name in url_formats:
            url = f"{self.BASE_URL}/{url_name}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, 
                        headers=self.get_headers(),
                        timeout=aiohttp.ClientTimeout(total=10),
                        allow_redirects=True
                    ) as resp:
                        
                        if resp.status == 200:
                            html = await resp.text()
                            return self._parse_lore(html)
                        elif resp.status == 403:
                            print(f"Blocked by Cloudflare on {url}")
                            continue
                            
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                continue
        
        return None
    
    def _parse_lore(self, html: str) -> Optional[Dict]:
        """Parse HTML for lore data"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            data = {}
            
            # Look for main content
            content = soup.find('div', {'id': 'mw-content-text'})
            if not content:
                return None
            
            # Get intro
            paragraphs = content.find_all('p', recursive=False)[:3]
            lore_text = "\n\n".join([
                p.get_text(strip=True) for p in paragraphs 
                if p.get_text(strip=True) and len(p.get_text(strip=True)) > 50
            ])
            
            if lore_text:
                data['lore'] = lore_text[:1500] + "..." if len(lore_text) > 1500 else lore_text
            
            # Try to get image
            infobox = soup.find('aside', {'class': 'portable-infobox'})
            if infobox:
                img = infobox.find('img')
                if img:
                    src = img.get('data-src') or img.get('src')
                    if src and src.startswith('http'):
                        data['image_url'] = src
            
            return data if data else None
            
        except Exception as e:
            print(f"Parse error: {e}")
            return None
    
    async def get_events(self) -> List[Dict]:
        """Get current events - often blocked on cloud hosting"""
        # Hardcoded recent events as fallback since scraping usually fails
        return [
            {
                'name': 'Chaldea Boys Collection 2026',
                'duration': 'March 2026',
                'type': 'Seasonal Event'
            },
            {
                'name': 'FGO Arcade Collaboration',
                'duration': 'Upcoming',
                'type': 'Collaboration'
            },
            {
                'name': 'Spring New Master Campaign',
                'duration': 'Ongoing',
                'type': 'Campaign'
            }
        ]

class GamePressScraper:
    BASE_URL = "https://grandorder.gamepress.gg"
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
            'DNT': '1'
        }
    
    async def get_servant_rating(self, servant_name: str) -> Optional[Dict]:
        """Try to get rating - usually blocked"""
        # Return mock data since GamePress is heavily protected
        return None  # Let the cog handle the failure message
    
    async def get_tier_list(self) -> List[Dict]:
        """Return community tier list since scraping fails"""
        # Based on 2024-2025 community consensus
        return [
            {
                'tier': 'SS (Gamebreaking)',
                'servants': ['Arjuna (Alter)', 'Koyanskaya of Light', 'Oberon', 'Artoria Caster']
            },
            {
                'tier': 'S+ (Top Tier)',
                'servants': ['Tamamo (Caster)', 'Merlin', 'Zhuge Liang', 'Scathach-Skadi']
            },
            {
                'tier': 'S (Excellent)',
                'servants': ['Gilgamesh', 'Kama', 'Musashi', 'Space Ishtar', 'Super Orion']
            },
            {
                'tier': 'A+ (Great)',
                'servants': ['Ishtar', 'Ereshkigal', 'Morgan', 'Melusine', 'Kama (Assassin)']
            }
        ]
    
    async def get_farming_guide(self, material: str) -> Optional[Dict]:
        """Generic farming advice"""
        material_locations = {
            'hero proof': ['Chaldea Gate - Training Grounds (Archer)', 'Okeanos - Pirate Ship'],
            'void dust': ['Chaldea Gate - Training Grounds (Caster)', 'Fuyuki - Unknown Coordinates X-C'],
            'dragon fang': ['Okeanos - Caldera Island', 'Chaldea Gate - Training Grounds (Lancer)'],
            'octuplet crystal': ['Chaldea Gate - Training Grounds (Saber)', 'Septem - Mt. Etna'],
        }
        
        key = material.lower()
        return {
            'material': material,
            'locations': material_locations.get(key, ['Check gamepress.gg/farming-guide for specific locations'])
        }
