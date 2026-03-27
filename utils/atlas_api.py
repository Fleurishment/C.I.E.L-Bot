import aiohttp
from typing import Optional, List, Dict, Any

class AtlasAPI:
    BASE_URL = "https://api.atlasacademy.io"
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
    
    async def search_servant(self, name: str, region: str = "NA") -> List[Dict]:
        """Search for servants by name"""
        url = f"{self.BASE_URL}/basic/{region}/servant/search"
        params = {"name": name, "lang": "en"}
        
        async with self.session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            return []
    
    async def get_servant_details(self, servant_id: int, region: str = "NA") -> Optional[Dict]:
        """Get detailed servant information"""
        url = f"{self.BASE_URL}/nice/{region}/servant/{servant_id}"
        
        async with self.session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            return None
    
    async def get_servant_assets(self, servant_id: int, region: str = "NA") -> Optional[Dict]:
        """Get servant artwork/assets"""
        url = f"{self.BASE_URL}/nice/{region}/svt/{servant_id}"
        
        async with self.session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('extraAssets', {})
            return {}
