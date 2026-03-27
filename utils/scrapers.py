import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import re
import aiohttp
import asyncio

class FandomScraper:
    BASE_URL = "https://fategrandorder.fandom.com/wiki"
    
    async def get_servant_lore(self, servant_name: str) -> Optional[Dict]:
        """Scrape servant lore and background from Fandom"""
        # Format name for URL (replace spaces with underscores)
        url_name = servant_name.replace(" ", "_").replace("(", "").replace(")", "")
        url = f"{self.BASE_URL}/{url_name}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
                    
            soup = BeautifulSoup(html, 'lxml')
            data = {}
            
            # Get introduction/lore
            intro_div = soup.find('div', {'class': 'mw-parser-output'})
            if intro_div:
                # Get first few paragraphs
                paragraphs = intro_div.find_all('p', recursive=False)[:3]
                lore_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                data['lore'] = lore_text[:1000] + "..." if len(lore_text) > 1000 else lore_text
            
            # Get biography sections
            biography = {}
            h2_tags = soup.find_all('h2')
            for h2 in h2_tags:
                span = h2.find('span', {'class': 'mw-headline'})
                if span and 'Biography' in span.get_text():
                    next_sibling = h2.find_next_sibling()
                    while next_sibling and next_sibling.name != 'h2':
                        if next_sibling.name == 'p':
                            bio_text = next_sibling.get_text(strip=True)
                            if bio_text:
                                biography['summary'] = bio_text[:1500]
                                break
                        next_sibling = next_sibling.find_next_sibling()
            
            data['biography'] = biography.get('summary', 'No biography found')
            
            # Get servant image from infobox
            infobox = soup.find('aside', {'class': 'portable-infobox'})
            if infobox:
                img = infobox.find('img')
                if img:
                    data['image_url'] = img.get('src', '')
            
            # Get interludes and strengthening quests info
            interlude_section = soup.find('span', {'id': re.compile('Interlude|Strengthen')})
            if interlude_section:
                interlude_data = []
                table = interlude_section.find_parent('h2').find_next_sibling('table')
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header
                    for row in rows[:3]:  # Limit to first 3
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            quest_name = cols[0].get_text(strip=True)
                            reward = cols[1].get_text(strip=True)
                            interlude_data.append(f"**{quest_name}**: {reward}")
                data['interludes'] = interlude_data
            
            return data
            
        except Exception as e:
            print(f"Fandom scraping error: {e}")
            return None
    
    async def get_events(self) -> List[Dict]:
        """Scrape current and upcoming events"""
        url = f"{self.BASE_URL}/Event_List"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'lxml')
            events = []
            
            # Find current events table
            tables = soup.find_all('table', {'class': 'wikitable'})
            for table in tables[:2]:  # Check first 2 tables
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows[:5]:  # Limit to 5 events
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        event_name = cols[0].get_text(strip=True)
                        duration = cols[1].get_text(strip=True)
                        event_type = cols[2].get_text(strip=True) if len(cols) > 2 else "N/A"
                        
                        events.append({
                            'name': event_name,
                            'duration': duration,
                            'type': event_type
                        })
            
            return events
            
        except Exception as e:
            print(f"Event scraping error: {e}")
            return []

class GamePressScraper:
    BASE_URL = "https://grandorder.gamepress.gg"
    
    async def get_servant_rating(self, servant_name: str) -> Optional[Dict]:
        """Scrape servant tier and ratings from GamePress"""
        search_name = servant_name.lower().replace(" ", "-")
        url = f"{self.BASE_URL}/servant/{search_name}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        # Try search page
                        return await self._search_gamepress(servant_name)
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'lxml')
            data = {}
            
            # Get tier rating
            tier_div = soup.find('div', {'class': 'servant-tier'})
            if tier_div:
                data['tier'] = tier_div.get_text(strip=True)
            
            # Get ratings
            ratings = {}
            rating_sections = soup.find_all('div', {'class': 'rating-section'})
            for section in rating_sections:
                label = section.find('div', {'class': 'rating-label'})
                value = section.find('div', {'class': 'rating-value'})
                if label and value:
                    ratings[label.get_text(strip=True)] = value.get_text(strip=True)
            
            data['ratings'] = ratings
            
            # Get pros and cons
            pros_cons = soup.find('div', {'class': 'pros-cons'})
            if pros_cons:
                pros = pros_cons.find('div', {'class': 'pros'})
                cons = pros_cons.find('div', {'class': 'cons'})
                if pros:
                    data['pros'] = [li.get_text(strip=True) for li in pros.find_all('li')[:3]]
                if cons:
                    data['cons'] = [li.get_text(strip=True) for li in cons.find_all('li')[:3]]
            
            # Get gameplay tips
            tips_section = soup.find('div', {'class': 'gameplay-tips'})
            if tips_section:
                tips = tips_section.find_all('li')[:3]
                data['tips'] = [tip.get_text(strip=True) for tip in tips]
            
            return data
            
        except Exception as e:
            print(f"GamePress scraping error: {e}")
            return None
    
    async def _search_gamepress(self, name: str) -> Optional[Dict]:
        """Fallback search on GamePress"""
        search_url = f"{self.BASE_URL}/search/content/{name.replace(' ', '%20')}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=10) as resp:
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'lxml')
            results = soup.find_all('li', {'class': 'search-result'})
            if results:
                first_link = results[0].find('a', href=True)
                if first_link and 'servant' in first_link['href']:
                    # Recursively call with correct URL
                    correct_name = first_link['href'].split('/')[-1]
                    return await self.get_servant_rating(correct_name.replace('-', ' '))
            return None
        except:
            return None
    
    async def get_tier_list(self) -> List[Dict]:
        """Scrape current tier list"""
        url = f"{self.BASE_URL}/tier-list"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'lxml')
            tiers = []
            
            tier_containers = soup.find_all('div', {'class': 'tier-row'})
            for container in tier_containers[:5]:  # Top 5 tiers
                tier_label = container.find('div', {'class': 'tier-label'})
                if tier_label:
                    tier_name = tier_label.get_text(strip=True)
                    servants = container.find_all('div', {'class': 'servant-icon'})
                    servant_list = []
                    
                    for servant in servants[:5]:  # Top 5 per tier
                        name_tag = servant.find('img')
                        if name_tag:
                            servant_list.append(name_tag.get('alt', 'Unknown'))
                    
                    tiers.append({
                        'tier': tier_name,
                        'servants': servant_list
                    })
            
            return tiers
            
        except Exception as e:
            print(f"Tier list scraping error: {e}")
            return []
    
    async def get_farming_guide(self, material: str) -> Optional[Dict]:
        """Scrape best farming locations for materials"""
        url = f"{self.BASE_URL}/farming-guide"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Search for material in page
            material_section = soup.find('div', string=re.compile(material, re.I))
            if material_section:
                parent = material_section.find_parent('div', {'class': 'material-section'})
                if parent:
                    locations = []
                    rows = parent.find_all('tr')[1:]
                    for row in rows[:3]:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            quest = cols[0].get_text(strip=True)
                            ap_efficiency = cols[1].get_text(strip=True)
                            locations.append(f"**{quest}**: {ap_efficiency} AP/drop")
                    
                    return {
                        'material': material,
                        'locations': locations
                    }
            return None
            
        except Exception as e:
            print(f"Farming guide error: {e}")
            return None
