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

class LoopNetScraper:
    """
    Scraper for LoopNet commercial property listings.
    """
    
    BASE_URL = "https://www.loopnet.com"
    SEARCH_URL = f"{BASE_URL}/search/commercial-real-estate"
    
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
        """Initialize the LoopNet scraper"""
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    @cache(ttl=3600, use_disk=True)
    def search_properties(self, location: str, property_type: Optional[str] = None,
                          min_price: Optional[int] = None, max_price: Optional[int] = None,
                          max_results: int = 20) -> List[Property]:
        """
        Search for commercial properties on LoopNet based on location and filters.
        
        Args:
            location: Location to search (city, state, ZIP)
            property_type: Type of commercial property (office, retail, industrial, multi-family, etc.)
            min_price: Minimum price filter
            max_price: Maximum price filter
            max_results: Maximum number of results to return
            
        Returns:
            List of Property objects
        """
        # Build the search URL with filters
        search_url = self._build_search_url(location, property_type, min_price, max_price)
        
        try:
            logger.info(f"Searching LoopNet for commercial properties in {location}")
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
            
            logger.info(f"Found {len(detailed_properties)} commercial properties on LoopNet")
            return detailed_properties
            
        except Exception as e:
            logger.error(f"Error searching LoopNet: {e}")
            return []
    
    def _build_search_url(self, location: str, property_type: Optional[str] = None,
                         min_price: Optional[int] = None, max_price: Optional[int] = None) -> str:
        """
        Build the search URL with the specified filters.
        
        Args:
            location: Location to search (city, state, ZIP)
            property_type: Type of commercial property (office, retail, industrial, multi-family, etc.)
            min_price: Minimum price filter
            max_price: Maximum price filter
            
        Returns:
            Complete search URL
        """
        # Format the location for the URL
        formatted_location = location.replace(' ', '-').replace(',', '').lower()
        
        # Start with the base search URL
        url = f"{self.SEARCH_URL}/for-sale/{formatted_location}"
        
        # Add property type if provided
        if property_type:
            property_type_slug = property_type.replace(' ', '-').lower()
            url = f"{self.SEARCH_URL}/{property_type_slug}-for-sale/{formatted_location}"
        
        # Add query parameters
        params = []
        if min_price:
            params.append(f"minprice={min_price}")
        if max_price:
            params.append(f"maxprice={max_price}")
        
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
        
        # Find property listing cards
        property_cards = soup.select(".placard, .property-card, .listing-card")
        
        for card in property_cards[:max_results]:
            try:
                prop_data = self._extract_property_from_card(card)
                if prop_data:
                    properties.append(prop_data)
            except Exception as e:
                logger.warning(f"Error extracting commercial property data from card: {e}")
        
        return properties
    
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
            link_elem = card.select_one("a.listing-card-link, a.placard-link, a.property-link")
            if not link_elem:
                return None
            
            property_url = link_elem.get('href', '')
            property_id = re.search(r'/(\d+)(?:\?|$)', property_url)
            property_id = property_id.group(1) if property_id else str(hash(property_url))
            
            # Extract the address
            address_elem = card.select_one(".listing-address, .placard-address, .property-address")
            address = address_elem.text.strip() if address_elem else ""
            
            # Extract city, state, zip
            location_elem = card.select_one(".listing-city, .placard-location, .property-location")
            location_text = location_elem.text.strip() if location_elem else ""
            city = ""
            state = ""
            zip_code = ""
            
            # Attempt to parse location (City, State ZIP)
            location_parts = location_text.split(',')
            if len(location_parts) > 0:
                city = location_parts[0].strip()
            if len(location_parts) > 1:
                state_zip = location_parts[1].strip().split(' ')
                state = state_zip[0] if state_zip else ""
                zip_code = state_zip[1] if len(state_zip) > 1 else ""
            
            # Extract the price
            price_elem = card.select_one(".price, .listing-price, .placard-price")
            price_text = price_elem.text.strip() if price_elem else "0"
            price = self._extract_price(price_text)
            
            # Extract property type
            property_type_elem = card.select_one(".property-type, .listing-type, .placard-type")
            property_type = property_type_elem.text.strip() if property_type_elem else "Commercial"
            
            # Extract square footage
            sqft_elem = card.select_one(".space, .listing-space, .placard-space")
            square_feet = None
            if sqft_elem:
                sqft_text = sqft_elem.text.strip()
                sqft_match = re.search(r'([\d,]+)\s*(?:SF|sq ft|sqft)', sqft_text, re.IGNORECASE)
                if sqft_match:
                    square_feet = self._safe_float(sqft_match.group(1).replace(',', ''))
            
            # Create basic Property object
            property_data = Property(
                id=property_id,
                source="LoopNet",
                property_url=property_url,
                property_type=property_type,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                price=price,
                square_feet=square_feet,
                raw_data={}
            )
            
            return property_data
        
        except Exception as e:
            logger.warning(f"Error extracting commercial property from card: {e}")
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
            logger.info(f"Getting details for commercial property: {property_data.property_url}")
            response = self.session.get(property_data.property_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract additional details from the property page
            self._extract_additional_details(soup, property_data)
            
            # Estimate rental value if not present
            if not property_data.annual_rent and not property_data.monthly_rent:
                annual_rent = self._estimate_commercial_rental_value(property_data)
                if annual_rent:
                    property_data.annual_rent = annual_rent
                    property_data.monthly_rent = annual_rent / 12
            
            return property_data
            
        except Exception as e:
            logger.error(f"Error getting commercial property details: {e}")
            return property_data
    
    def _extract_additional_details(self, soup: BeautifulSoup, property_data: Property) -> None:
        """
        Extract additional details from the property page.
        
        Args:
            soup: BeautifulSoup object for the property page
            property_data: Property object to update with additional details
        """
        # Extract property description
        description_elem = soup.select_one(".description-text, .listing-description, #descriptionSection")
        if description_elem:
            property_data.description = description_elem.text.strip()
        
        # Extract the year built
        year_built_label = soup.find(string=re.compile("Year Built", re.IGNORECASE))
        if year_built_label:
            parent = year_built_label.parent
            value_elem = parent.find_next_sibling()
            if value_elem:
                try:
                    year_text = value_elem.text.strip()
                    year_match = re.search(r'(\d{4})', year_text)
                    if year_match:
                        property_data.year_built = int(year_match.group(1))
                except ValueError:
                    pass
        
        # Extract lot size
        lot_size_label = soup.find(string=re.compile("Lot Size", re.IGNORECASE))
        if lot_size_label:
            parent = lot_size_label.parent
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
        
        # Extract cap rate if available
        cap_rate_label = soup.find(string=re.compile("Cap Rate", re.IGNORECASE))
        if cap_rate_label:
            parent = cap_rate_label.parent
            value_elem = parent.find_next_sibling()
            if value_elem:
                cap_rate_text = value_elem.text.strip()
                cap_rate_match = re.search(r'([\d.]+)', cap_rate_text)
                if cap_rate_match:
                    try:
                        property_data.cap_rate = float(cap_rate_match.group(1))
                    except ValueError:
                        pass
        
        # Extract NOI if available
        noi_label = soup.find(string=re.compile("Net Operating Income|NOI", re.IGNORECASE))
        if noi_label:
            parent = noi_label.parent
            value_elem = parent.find_next_sibling()
            if value_elem:
                noi_text = value_elem.text.strip()
                noi = self._extract_price(noi_text)
                
                # Calculate annual rent from NOI if cap rate is available
                if noi and property_data.cap_rate:
                    property_data.annual_rent = noi
                    property_data.monthly_rent = noi / 12
        
        # Extract features and amenities
        features = []
        features_section = soup.find(string=re.compile("Features|Amenities", re.IGNORECASE))
        if features_section:
            features_list = features_section.find_next('ul')
            if features_list:
                for item in features_list.find_all('li'):
                    features.append(item.text.strip())
        
        property_data.features = features
        
        # Extract image URLs
        image_urls = []
        for img in soup.select(".slide img, .carousel img, .listing-image img"):
            if 'src' in img.attrs:
                image_urls.append(img['src'])
        
        property_data.image_urls = image_urls
        
        # Extract lat/long if available
        script_data = soup.find('script', string=re.compile('latitude|longitude'))
        if script_data and script_data.string:
            lat_match = re.search(r'"latitude":\s*([\d.-]+)', script_data.string)
            lng_match = re.search(r'"longitude":\s*([\d.-]+)', script_data.string)
            
            if lat_match and lng_match:
                try:
                    property_data.latitude = float(lat_match.group(1))
                    property_data.longitude = float(lng_match.group(1))
                except ValueError:
                    pass
    
    def _estimate_commercial_rental_value(self, property_data: Property) -> Optional[float]:
        """
        Estimate annual rental value for a commercial property based on its characteristics.
        
        Args:
            property_data: Property object with basic information
            
        Returns:
            Estimated annual rent or None if estimation fails
        """
        # For commercial properties, try to calculate rental value based on typical cap rates
        # Use this as a fallback when actual values aren't available
        if property_data.price and property_data.square_feet:
            # Estimated cap rate based on property type (simplified)
            cap_rate = 0.07  # Default 7% cap rate
            
            property_type_lower = property_data.property_type.lower()
            if 'office' in property_type_lower:
                cap_rate = 0.065  # 6.5% for office
            elif 'retail' in property_type_lower:
                cap_rate = 0.06   # 6% for retail
            elif 'industrial' in property_type_lower:
                cap_rate = 0.075  # 7.5% for industrial
            elif 'multi-family' in property_type_lower or 'apartment' in property_type_lower:
                cap_rate = 0.055  # 5.5% for multi-family
            
            # Estimate NOI based on cap rate and price
            annual_noi = property_data.price * cap_rate
            
            # Use NOI as an estimate of annual rent for commercial properties
            # This is a simplification - in reality, NOI = Rent - Operating Expenses
            return annual_noi
        
        return None
    
    @staticmethod
    def _extract_price(price_text: str) -> Optional[float]:
        """
        Extract numeric price from a price string.
        
        Args:
            price_text: Price string (e.g., "$500,000", "$2.5M")
            
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
