import requests
import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from models.property import Property
from utils.cache_utils import cache

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZillowScraper:
    """
    Scraper for Zillow property listings.
    """
    
    BASE_URL = "https://www.zillow.com"
    SEARCH_URL = f"{BASE_URL}/homes/for_sale/"
    RENT_ESTIMATE_URL = f"{BASE_URL}/rental-manager/calculator/rent-zestimate"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }
    
    def __init__(self):
        """Initialize the Zillow scraper"""
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    @cache(ttl=3600, use_disk=True)
    def search_properties(self, location: str, min_price: Optional[int] = None, 
                         max_price: Optional[int] = None, property_type: Optional[str] = None,
                         max_results: int = 20) -> List[Property]:
        """
        Search for properties on Zillow based on location and filters.
        
        Args:
            location: Location to search (city, neighborhood, ZIP)
            min_price: Minimum price filter
            max_price: Maximum price filter
            property_type: Type of property (house, apartment, condo, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of Property objects
        """
        # Build the search URL with filters
        search_url = self._build_search_url(location, min_price, max_price, property_type)
        
        try:
            logger.info(f"Searching Zillow for properties in {location}")
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            # Extract property data from the search results page
            properties = self._extract_properties_from_search(response.text, max_results)
            
            # Get additional details for each property
            detailed_properties = []
            for prop in properties[:max_results]:
                try:
                    if prop.property_url.startswith('/'):
                        prop.property_url = f"{self.BASE_URL}{prop.property_url}"
                    
                    detailed_prop = self._get_property_details(prop)
                    detailed_properties.append(detailed_prop)
                except Exception as e:
                    logger.error(f"Error getting details for {prop.property_url}: {e}")
            
            logger.info(f"Found {len(detailed_properties)} properties on Zillow")
            return detailed_properties
            
        except Exception as e:
            logger.error(f"Error searching Zillow: {e}")
            return []
    
    def _build_search_url(self, location: str, min_price: Optional[int] = None, 
                         max_price: Optional[int] = None, property_type: Optional[str] = None) -> str:
        """
        Build the search URL with the specified filters.
        
        Args:
            location: Location to search (city, neighborhood, ZIP)
            min_price: Minimum price filter
            max_price: Maximum price filter
            property_type: Type of property (house, apartment, condo, etc.)
            
        Returns:
            Complete search URL
        """
        # Format the location for the URL
        formatted_location = location.replace(' ', '-').replace(',', '').lower()
        
        # Start with the base search URL
        url = f"{self.SEARCH_URL}{formatted_location}/"
        
        # Add query parameters
        params = []
        if min_price:
            params.append(f"price_min={min_price}")
        if max_price:
            params.append(f"price_max={max_price}")
        if property_type:
            params.append(f"home_type={property_type}")
        
        # Add the parameters to the URL
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def _extract_properties_from_search(self, html_content: str, max_results: int) -> List[Property]:
        """
        Extract property data from the search results page.
        
        Args:
            html_content: HTML content of the search results page
            max_results: Maximum number of results to extract
            
        Returns:
            List of Property objects with basic information
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        properties = []
        
        # Look for the script containing the property data
        for script in soup.find_all('script'):
            if script.string and 'data-zrr-shared-data-key' in script.attrs:
                # Found the script with property data
                try:
                    # Extract the JSON data from the script
                    json_str = script.string.strip()
                    json_str = json_str.replace('<!--', '').replace('-->', '')
                    data = json.loads(json_str)
                    
                    # Extract the search results
                    search_results = data.get('cat1', {}).get('searchResults', {}).get('listResults', [])
                    
                    for result in search_results[:max_results]:
                        try:
                            prop_data = self._extract_property_from_result(result)
                            properties.append(prop_data)
                        except Exception as e:
                            logger.warning(f"Error extracting property data: {e}")
                    
                    break
                except Exception as e:
                    logger.error(f"Error parsing search results JSON: {e}")
        
        # If we couldn't extract properties from the script, try extracting from the HTML
        if not properties:
            # Fallback to scraping the HTML
            property_cards = soup.select("div[data-test='property-card']")
            
            for card in property_cards[:max_results]:
                try:
                    prop_data = self._extract_property_from_card(card)
                    if prop_data:
                        properties.append(prop_data)
                except Exception as e:
                    logger.warning(f"Error extracting property data from card: {e}")
        
        return properties
    
    def _extract_property_from_result(self, result: Dict[str, Any]) -> Property:
        """
        Extract property data from a search result JSON object.
        
        Args:
            result: JSON object containing property data
            
        Returns:
            Property object with basic information
        """
        # Extract the basic property information
        property_id = str(result.get('id', ''))
        address = result.get('address', '')
        price = self._extract_price(result.get('price', ''))
        property_url = result.get('detailUrl', '')
        
        # Extract location details
        city = result.get('addressCity', '')
        state = result.get('addressState', '')
        zip_code = result.get('addressZipcode', '')
        
        # Extract property characteristics
        bedrooms = self._safe_float(result.get('beds'))
        bathrooms = self._safe_float(result.get('baths'))
        square_feet = self._safe_float(result.get('area'))
        
        # Determine property type
        property_type = result.get('hdpData', {}).get('homeInfo', {}).get('homeType', 'Unknown')
        
        # Create basic Property object
        property_data = Property(
            id=property_id,
            source="Zillow",
            property_url=property_url,
            property_type=property_type,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            square_feet=square_feet,
            raw_data=result
        )
        
        return property_data
    
    def _extract_property_from_card(self, card) -> Optional[Property]:
        """
        Extract property data from an HTML property card.
        
        Args:
            card: BeautifulSoup object for a property card
            
        Returns:
            Property object with basic information or None if extraction fails
        """
        try:
            # Extract the property URL and ID
            link_elem = card.select_one("a[data-test='property-card-link']")
            if not link_elem:
                return None
            
            property_url = link_elem.get('href', '')
            property_id = property_url.split('/')[-1].split('_')[0]
            
            # Extract the address
            address_elem = card.select_one("address")
            address = address_elem.text.strip() if address_elem else ""
            
            # Split address into components (basic approach)
            address_parts = address.split(', ')
            city = address_parts[1] if len(address_parts) > 1 else ""
            state_zip = address_parts[2] if len(address_parts) > 2 else ""
            state_zip_parts = state_zip.split(' ')
            state = state_zip_parts[0] if state_zip_parts else ""
            zip_code = state_zip_parts[1] if len(state_zip_parts) > 1 else ""
            
            # Extract the price
            price_elem = card.select_one("[data-test='property-card-price']")
            price_text = price_elem.text.strip() if price_elem else "0"
            price = self._extract_price(price_text)
            
            # Extract bedrooms, bathrooms, square footage
            details_elem = card.select_one("[data-test='property-card-details']")
            details_text = details_elem.text.strip() if details_elem else ""
            
            bedrooms = None
            bathrooms = None
            square_feet = None
            
            # Parse details text (format like "3 bds | 2 ba | 1,500 sqft")
            details_parts = details_text.split('|')
            for part in details_parts:
                part = part.strip().lower()
                if 'bd' in part:
                    bedrooms = self._safe_float(part.split(' ')[0])
                elif 'ba' in part:
                    bathrooms = self._safe_float(part.split(' ')[0])
                elif 'sqft' in part:
                    square_feet = self._safe_float(part.replace(',', '').split(' ')[0])
            
            # Determine property type (simplified for HTML scraping)
            property_type_elem = card.select_one("[data-test='property-card-home-type']")
            property_type = property_type_elem.text.strip() if property_type_elem else "Unknown"
            
            # Create basic Property object
            property_data = Property(
                id=property_id,
                source="Zillow",
                property_url=property_url,
                property_type=property_type,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                price=price,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                square_feet=square_feet,
                raw_data={}
            )
            
            return property_data
        
        except Exception as e:
            logger.warning(f"Error extracting property from card: {e}")
            return None
    
    @cache(ttl=86400, use_disk=True)
    def _get_property_details(self, property_data: Property) -> Property:
        """
        Get additional details for a property from its dedicated page.
        
        Args:
            property_data: Basic Property object with property_url
            
        Returns:
            Property object with additional details
        """
        try:
            logger.info(f"Getting details for property: {property_data.property_url}")
            response = self.session.get(property_data.property_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract additional details from the property page
            self._extract_additional_details(soup, property_data)
            
            # Estimate rental value if not present
            if not property_data.monthly_rent:
                property_data.monthly_rent = self._estimate_rental_value(property_data)
                if property_data.monthly_rent:
                    property_data.annual_rent = property_data.monthly_rent * 12
            
            return property_data
            
        except Exception as e:
            logger.error(f"Error getting property details: {e}")
            return property_data
    
    def _extract_additional_details(self, soup: BeautifulSoup, property_data: Property) -> None:
        """
        Extract additional details from the property page.
        
        Args:
            soup: BeautifulSoup object for the property page
            property_data: Property object to update with additional details
        """
        # Extract property description
        description_elem = soup.select_one("[data-testid='description']")
        if description_elem:
            property_data.description = description_elem.text.strip()
        
        # Extract the year built
        year_built_elem = soup.find(string=re.compile("Year built", re.IGNORECASE))
        if year_built_elem:
            parent = year_built_elem.parent
            value_elem = parent.find_next_sibling()
            if value_elem:
                try:
                    property_data.year_built = int(value_elem.text.strip())
                except ValueError:
                    pass
        
        # Extract lot size
        lot_size_elem = soup.find(string=re.compile("Lot", re.IGNORECASE))
        if lot_size_elem:
            parent = lot_size_elem.parent
            value_elem = parent.find_next_sibling()
            if value_elem:
                lot_size_text = value_elem.text.strip()
                # Extract numeric value from text (e.g., "0.25 acres" -> 0.25)
                lot_size_match = re.search(r'([\d.,]+)', lot_size_text)
                if lot_size_match:
                    try:
                        property_data.lot_size = float(lot_size_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
        
        # Extract monthly rent if available
        rent_elem = soup.find(string=re.compile("Rent (?:Zestimate|estimate)", re.IGNORECASE))
        if rent_elem:
            parent = rent_elem.parent
            value_elem = parent.find_next_sibling()
            if value_elem:
                rent_text = value_elem.text.strip()
                property_data.monthly_rent = self._extract_price(rent_text)
                if property_data.monthly_rent:
                    property_data.annual_rent = property_data.monthly_rent * 12
        
        # Extract features and amenities
        features = []
        features_section = soup.find(string=re.compile("Features", re.IGNORECASE))
        if features_section:
            features_list = features_section.find_next('ul')
            if features_list:
                for item in features_list.find_all('li'):
                    features.append(item.text.strip())
        
        property_data.features = features
        
        # Extract image URLs
        image_urls = []
        for img in soup.select("img[src*='images.zillow']"):
            if 'src' in img.attrs:
                image_urls.append(img['src'])
        
        property_data.image_urls = image_urls
        
        # Extract lat/long if available
        for script in soup.find_all('script'):
            if script.string and 'latitude' in script.string:
                lat_match = re.search(r'"latitude":\s*([\d.-]+)', script.string)
                lng_match = re.search(r'"longitude":\s*([\d.-]+)', script.string)
                
                if lat_match and lng_match:
                    try:
                        property_data.latitude = float(lat_match.group(1))
                        property_data.longitude = float(lng_match.group(1))
                    except ValueError:
                        pass
                break
        
        # Extract date listed if available
        date_elem = soup.find(string=re.compile("Date listed", re.IGNORECASE))
        if date_elem:
            parent = date_elem.parent
            value_elem = parent.find_next_sibling()
            if value_elem:
                date_text = value_elem.text.strip()
                try:
                    # Parse date text (format varies)
                    property_data.date_listed = datetime.strptime(date_text, '%m/%d/%Y')
                except ValueError:
                    try:
                        property_data.date_listed = datetime.strptime(date_text, '%b %d, %Y')
                    except ValueError:
                        pass
    
    def _estimate_rental_value(self, property_data: Property) -> Optional[float]:
        """
        Estimate the rental value for a property based on its characteristics.
        
        Args:
            property_data: Property object with basic information
            
        Returns:
            Estimated monthly rent or None if estimation fails
        """
        # Simple rental value estimation (1% rule as fallback)
        if property_data.price:
            # Apply a more conservative estimate than the 1% rule
            # Use 0.7% for higher-priced properties and 0.8% for lower-priced properties
            if property_data.price > 500000:
                monthly_rent = property_data.price * 0.007
            else:
                monthly_rent = property_data.price * 0.008
            
            # Round to nearest $50
            monthly_rent = round(monthly_rent / 50) * 50
            
            return monthly_rent
        
        return None
    
    @staticmethod
    def _extract_price(price_text: str) -> Optional[float]:
        """
        Extract numeric price from a price string.
        
        Args:
            price_text: Price string (e.g., "$500,000", "$2.5K")
            
        Returns:
            Numeric price or None if extraction fails
        """
        try:
            # Remove non-numeric characters except for dots
            price_text = price_text.strip()
            
            # Handle abbreviations (K for thousands, M for millions)
            multiplier = 1
            if 'K' in price_text:
                multiplier = 1000
                price_text = price_text.replace('K', '')
            elif 'M' in price_text:
                multiplier = 1000000
                price_text = price_text.replace('M', '')
            
            # Remove $ and commas
            price_text = price_text.replace('$', '').replace(',', '')
            
            # Extract the numeric value
            match = re.search(r'([\d.]+)', price_text)
            if match:
                return float(match.group(1)) * multiplier
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """
        Safely convert a value to float.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None if conversion fails
        """
        if value is None:
            return None
        
        try:
            if isinstance(value, str):
                # Remove commas and other non-numeric characters
                value = re.sub(r'[^\d.]', '', value)
            return float(value)
        except (ValueError, TypeError):
            return None
