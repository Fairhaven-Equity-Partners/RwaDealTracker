from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Property:
    """
    Unified data model for properties from different sources.
    Standardizes property data into a consistent format.
    """
    # Basic information
    id: str
    source: str  # Platform source (Zillow, LoopNet, etc.)
    property_url: str
    property_type: str  # residential, commercial, multi-family, etc.
    
    # Location details
    address: str
    city: str
    state: str
    zip_code: str
    
    # Property characteristics
    price: float
    
    # Optional fields
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bedrooms: Optional[float] = None  # Can be decimal for commercial partial units
    bathrooms: Optional[float] = None
    square_feet: Optional[float] = None
    lot_size: Optional[float] = None
    year_built: Optional[int] = None
    
    # Financial metrics
    monthly_rent: Optional[float] = None
    annual_rent: Optional[float] = None
    rental_yield: Optional[float] = None  # Annual rent / Price
    cap_rate: Optional[float] = None  # NOI / Price
    price_to_rent_ratio: Optional[float] = None  # Price / Annual rent
    estimated_monthly_mortgage: Optional[float] = None
    
    # Risk assessment fields
    risk_level: Optional[str] = None  # low, medium, high
    vacancy_rate: Optional[float] = None
    
    # Location metrics
    location_score: Optional[float] = None
    population_growth: Optional[float] = None
    job_growth: Optional[float] = None
    
    # Additional details
    description: Optional[str] = None
    features: List[str] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    date_listed: Optional[datetime] = None
    
    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Calculated financial metrics will be populated by the financial analysis module
    financial_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate basic financial metrics if possible"""
        # Calculate rental yield if we have annual rent and price
        if self.annual_rent and self.price and self.price > 0:
            self.rental_yield = (self.annual_rent / self.price) * 100
            
        # Calculate price to rent ratio if we have annual rent and price
        if self.annual_rent and self.price and self.annual_rent > 0:
            self.price_to_rent_ratio = self.price / self.annual_rent
            
        # If we have monthly rent but not annual, calculate annual
        if self.monthly_rent and not self.annual_rent:
            self.annual_rent = self.monthly_rent * 12
            # Recalculate yield and ratio
            if self.price and self.price > 0:
                self.rental_yield = (self.annual_rent / self.price) * 100
                self.price_to_rent_ratio = self.price / self.annual_rent
                
        # If we have annual rent but not monthly, calculate monthly
        if self.annual_rent and not self.monthly_rent:
            self.monthly_rent = self.annual_rent / 12
