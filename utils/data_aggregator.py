import logging
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable
from models.property import Property
from scrapers.zillow_scraper import ZillowScraper
from scrapers.loopnet_scraper import LoopNetScraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataAggregator:
    """
    Aggregates property data from multiple sources.
    """
    
    def __init__(self):
        """Initialize the data aggregators and scrapers"""
        self.zillow_scraper = ZillowScraper()
        self.loopnet_scraper = LoopNetScraper()
        self.all_properties = []
    
    def fetch_properties(self, location: str, property_types: List[str] = None,
                         min_price: Optional[int] = None, max_price: Optional[int] = None,
                         max_results_per_source: int = 20) -> List[Property]:
        """
        Fetch properties from all available sources.
        
        Args:
            location: Location to search (city, state, ZIP)
            property_types: List of property types to include
            min_price: Minimum price filter
            max_price: Maximum price filter
            max_results_per_source: Maximum results to fetch from each source
            
        Returns:
            List of Property objects from all sources
        """
        # Reset properties list
        self.all_properties = []
        
        # Define sources to fetch from
        sources = [
            {
                "name": "Zillow",
                "fetch_function": self._fetch_from_zillow,
                "args": {
                    "location": location,
                    "min_price": min_price,
                    "max_price": max_price,
                    "max_results": max_results_per_source
                }
            },
            {
                "name": "LoopNet",
                "fetch_function": self._fetch_from_loopnet,
                "args": {
                    "location": location,
                    "min_price": min_price,
                    "max_price": max_price,
                    "max_results": max_results_per_source
                }
            }
        ]
        
        # Fetch properties from all sources in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
            future_to_source = {
                executor.submit(source["fetch_function"], **source["args"]): source["name"]
                for source in sources
            }
            
            for future in concurrent.futures.as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    properties = future.result()
                    logger.info(f"Fetched {len(properties)} properties from {source_name}")
                    self.all_properties.extend(properties)
                except Exception as e:
                    logger.error(f"Error fetching from {source_name}: {e}")
        
        # Filter by property types if provided
        if property_types:
            property_types_lower = [pt.lower() for pt in property_types]
            self.all_properties = [
                p for p in self.all_properties 
                if p.property_type and any(pt in p.property_type.lower() for pt in property_types_lower)
            ]
        
        logger.info(f"Total properties after aggregation: {len(self.all_properties)}")
        return self.all_properties
    
    def _fetch_from_zillow(self, location: str, min_price: Optional[int] = None,
                         max_price: Optional[int] = None, max_results: int = 20) -> List[Property]:
        """
        Fetch residential properties from Zillow.
        
        Args:
            location: Location to search
            min_price: Minimum price filter
            max_price: Maximum price filter
            max_results: Maximum results to fetch
            
        Returns:
            List of Property objects from Zillow
        """
        try:
            return self.zillow_scraper.search_properties(
                location=location,
                min_price=min_price,
                max_price=max_price,
                max_results=max_results
            )
        except Exception as e:
            logger.error(f"Error fetching from Zillow: {e}")
            return []
    
    def _fetch_from_loopnet(self, location: str, min_price: Optional[int] = None,
                           max_price: Optional[int] = None, max_results: int = 20) -> List[Property]:
        """
        Fetch commercial properties from LoopNet.
        
        Args:
            location: Location to search
            min_price: Minimum price filter
            max_price: Maximum price filter
            max_results: Maximum results to fetch
            
        Returns:
            List of Property objects from LoopNet
        """
        try:
            return self.loopnet_scraper.search_properties(
                location=location,
                min_price=min_price,
                max_price=max_price,
                max_results=max_results
            )
        except Exception as e:
            logger.error(f"Error fetching from LoopNet: {e}")
            return []
    
    def sort_properties(self, properties: List[Property], sort_by: str, reverse: bool = True) -> List[Property]:
        """
        Sort properties by a specified metric.
        
        Args:
            properties: List of Property objects to sort
            sort_by: Metric to sort by (price, rental_yield, cap_rate, etc.)
            reverse: Whether to reverse the order (descending)
            
        Returns:
            Sorted list of Property objects
        """
        if not properties:
            return []
        
        # Define sorting key functions
        sort_keys = {
            "price": lambda p: p.price if p.price is not None else float('inf'),
            "price_asc": lambda p: p.price if p.price is not None else float('inf'),
            "rental_yield": lambda p: p.rental_yield if p.rental_yield is not None else float('-inf'),
            "cap_rate": lambda p: p.cap_rate if p.cap_rate is not None else float('-inf'),
            "price_to_rent": lambda p: p.price_to_rent_ratio if p.price_to_rent_ratio is not None else float('inf'),
            "square_feet": lambda p: p.square_feet if p.square_feet is not None else 0,
            "bedrooms": lambda p: p.bedrooms if p.bedrooms is not None else 0,
            "bathrooms": lambda p: p.bathrooms if p.bathrooms is not None else 0,
            "year_built": lambda p: p.year_built if p.year_built is not None else 0,
            "cash_flow": lambda p: p.financial_metrics.get("monthly_cash_flow", 0) if p.financial_metrics else 0,
            "cash_on_cash": lambda p: p.financial_metrics.get("cash_on_cash_return", 0) if p.financial_metrics else 0,
            "risk_score": lambda p: p.financial_metrics.get("risk_score", float('inf')) if p.financial_metrics else float('inf')
        }
        
        # Select sort key function
        if sort_by in sort_keys:
            key_func = sort_keys[sort_by]
            # For price_asc, we override the reverse flag
            if sort_by == "price_asc":
                reverse = False
            # For risk_score, lower is better so reverse the order
            if sort_by == "risk_score":
                reverse = not reverse
            
            return sorted(properties, key=key_func, reverse=reverse)
        
        # Default to sorting by price if the sort_by key is not recognized
        return sorted(properties, key=sort_keys["price"], reverse=reverse)
    
    def filter_properties(self, properties: List[Property], filters: Dict[str, Any]) -> List[Property]:
        """
        Filter properties based on various criteria.
        
        Args:
            properties: List of Property objects to filter
            filters: Dictionary of filter criteria
            
        Returns:
            Filtered list of Property objects
        """
        filtered_properties = properties.copy()
        
        # Filter by source platforms
        if "sources" in filters and filters["sources"]:
            filtered_properties = [p for p in filtered_properties if p.source in filters["sources"]]
        
        # Filter by property type
        if "property_types" in filters and filters["property_types"]:
            property_types_lower = [pt.lower() for pt in filters["property_types"]]
            filtered_properties = [
                p for p in filtered_properties 
                if p.property_type and any(pt in p.property_type.lower() for pt in property_types_lower)
            ]
        
        # Filter by price range
        if "min_price" in filters and filters["min_price"] is not None:
            filtered_properties = [p for p in filtered_properties if p.price and p.price >= filters["min_price"]]
        
        if "max_price" in filters and filters["max_price"] is not None:
            filtered_properties = [p for p in filtered_properties if p.price and p.price <= filters["max_price"]]
        
        # Filter by bedrooms range (for residential properties)
        if "min_bedrooms" in filters and filters["min_bedrooms"] is not None:
            filtered_properties = [p for p in filtered_properties if p.bedrooms and p.bedrooms >= filters["min_bedrooms"]]
        
        if "max_bedrooms" in filters and filters["max_bedrooms"] is not None:
            filtered_properties = [p for p in filtered_properties if p.bedrooms and p.bedrooms <= filters["max_bedrooms"]]
        
        # Filter by rental yield range
        if "min_rental_yield" in filters and filters["min_rental_yield"] is not None:
            filtered_properties = [p for p in filtered_properties if p.rental_yield and p.rental_yield >= filters["min_rental_yield"]]
        
        if "max_rental_yield" in filters and filters["max_rental_yield"] is not None:
            filtered_properties = [p for p in filtered_properties if p.rental_yield and p.rental_yield <= filters["max_rental_yield"]]
        
        # Filter by cap rate range
        if "min_cap_rate" in filters and filters["min_cap_rate"] is not None:
            filtered_properties = [
                p for p in filtered_properties 
                if (p.cap_rate and p.cap_rate >= filters["min_cap_rate"]) or
                   (p.financial_metrics and p.financial_metrics.get("cap_rate", 0) >= filters["min_cap_rate"])
            ]
        
        if "max_cap_rate" in filters and filters["max_cap_rate"] is not None:
            filtered_properties = [
                p for p in filtered_properties 
                if (p.cap_rate and p.cap_rate <= filters["max_cap_rate"]) or
                   (p.financial_metrics and p.financial_metrics.get("cap_rate", 0) <= filters["max_cap_rate"])
            ]
        
        # Filter by square footage range
        if "min_square_feet" in filters and filters["min_square_feet"] is not None:
            filtered_properties = [p for p in filtered_properties if p.square_feet and p.square_feet >= filters["min_square_feet"]]
        
        if "max_square_feet" in filters and filters["max_square_feet"] is not None:
            filtered_properties = [p for p in filtered_properties if p.square_feet and p.square_feet <= filters["max_square_feet"]]
        
        # Filter by year built range
        if "min_year_built" in filters and filters["min_year_built"] is not None:
            filtered_properties = [p for p in filtered_properties if p.year_built and p.year_built >= filters["min_year_built"]]
        
        if "max_year_built" in filters and filters["max_year_built"] is not None:
            filtered_properties = [p for p in filtered_properties if p.year_built and p.year_built <= filters["max_year_built"]]
        
        # Filter by cash flow (if financial metrics are available)
        if "min_cash_flow" in filters and filters["min_cash_flow"] is not None:
            filtered_properties = [
                p for p in filtered_properties 
                if p.financial_metrics and p.financial_metrics.get("monthly_cash_flow", 0) >= filters["min_cash_flow"]
            ]
        
        # Filter by risk level
        if "risk_levels" in filters and filters["risk_levels"]:
            risk_levels = [r.lower() for r in filters["risk_levels"]]
            filtered_properties = [
                p for p in filtered_properties 
                if (p.risk_level and p.risk_level.lower() in risk_levels) or
                   (p.financial_metrics and p.financial_metrics.get("risk_level", "").lower() in risk_levels)
            ]
        
        # Filter by location
        if "locations" in filters and filters["locations"]:
            locations_lower = [loc.lower() for loc in filters["locations"]]
            filtered_properties = [
                p for p in filtered_properties 
                if (p.city and p.city.lower() in locations_lower) or
                   (p.state and p.state.lower() in locations_lower) or
                   (p.zip_code and p.zip_code in filters["locations"])
            ]
        
        return filtered_properties
