import streamlit as st
from typing import Dict, Any, List, Callable, Optional, Tuple

def render_search_filters() -> Dict[str, Any]:
    """
    Render search filters UI components.
    
    Returns:
        Dictionary of filter values
    """
    with st.expander("Search Filters", expanded=True):
        # Create columns for side-by-side inputs
        col1, col2 = st.columns(2)
        
        with col1:
            location = st.text_input("Location (City, State, or ZIP)", "New York, NY")
        
        # Create price range slider
        price_min, price_max = st.slider(
            "Price Range ($)",
            min_value=0,
            max_value=2000000,
            value=(200000, 800000),
            step=50000,
            format="$%d"
        )
        
        # Create columns for additional filters
        col1, col2 = st.columns(2)
        
        with col1:
            property_types = st.multiselect(
                "Property Types",
                options=["Residential", "Multi-Family", "Commercial", "Office", "Retail", "Industrial"],
                default=["Residential", "Multi-Family"]
            )
        
        with col2:
            sources = st.multiselect(
                "Data Sources",
                options=["Zillow", "LoopNet"],
                default=["Zillow", "LoopNet"]
            )
        
        # Create a button to submit the search
        search_button = st.button("Search Properties", type="primary")
        
        # Return the filter values
        return {
            "location": location,
            "min_price": price_min,
            "max_price": price_max,
            "property_types": property_types,
            "sources": sources,
            "search_clicked": search_button
        }

def render_advanced_filters() -> Dict[str, Any]:
    """
    Render advanced filtering options.
    
    Returns:
        Dictionary of advanced filter values
    """
    with st.expander("Advanced Filters", expanded=False):
        # Create columns for rental yield filters
        col1, col2 = st.columns(2)
        
        with col1:
            min_rental_yield = st.number_input(
                "Min Rental Yield (%)",
                min_value=0.0,
                max_value=20.0,
                value=0.0,
                step=0.5
            )
        
        with col2:
            min_cap_rate = st.number_input(
                "Min Cap Rate (%)",
                min_value=0.0,
                max_value=20.0,
                value=0.0,
                step=0.5
            )
        
        # Bedrooms and Bathrooms for residential properties
        col1, col2 = st.columns(2)
        
        with col1:
            bedrooms = st.select_slider(
                "Bedrooms",
                options=[0, 1, 2, 3, 4, 5, "6+"],
                value=0
            )
            min_bedrooms = None if bedrooms == 0 else (6 if bedrooms == "6+" else bedrooms)
        
        with col2:
            bathrooms = st.select_slider(
                "Bathrooms",
                options=[0, 1, 2, 3, 4, 5, "6+"],
                value=0
            )
            min_bathrooms = None if bathrooms == 0 else (6 if bathrooms == "6+" else bathrooms)
        
        # Square footage range
        square_feet_min, square_feet_max = st.slider(
            "Square Footage",
            min_value=0,
            max_value=10000,
            value=(0, 10000),
            step=100
        )
        min_square_feet = None if square_feet_min == 0 else square_feet_min
        max_square_feet = None if square_feet_max == 10000 else square_feet_max
        
        # Year built range
        year_built_min, year_built_max = st.slider(
            "Year Built",
            min_value=1900,
            max_value=2023,
            value=(1900, 2023),
            step=5
        )
        min_year_built = None if year_built_min == 1900 else year_built_min
        max_year_built = None if year_built_max == 2023 else year_built_max
        
        # Cash flow filter
        min_cash_flow = st.number_input(
            "Min Monthly Cash Flow ($)",
            min_value=0,
            max_value=10000,
            value=0,
            step=100
        )
        min_cash_flow = None if min_cash_flow == 0 else min_cash_flow
        
        # Risk level filter
        risk_levels = st.multiselect(
            "Risk Levels",
            options=["Low", "Moderate", "High"],
            default=[]
        )
        
        # Return advanced filter values
        return {
            "min_rental_yield": min_rental_yield if min_rental_yield > 0 else None,
            "min_cap_rate": min_cap_rate if min_cap_rate > 0 else None,
            "min_bedrooms": min_bedrooms,
            "min_bathrooms": min_bathrooms,
            "min_square_feet": min_square_feet,
            "max_square_feet": max_square_feet,
            "min_year_built": min_year_built,
            "max_year_built": max_year_built,
            "min_cash_flow": min_cash_flow,
            "risk_levels": risk_levels
        }

def render_sorting_options(properties_count: int) -> Tuple[str, bool]:
    """
    Render sorting options for the property list.
    
    Args:
        properties_count: Number of properties in the current list
        
    Returns:
        Tuple of (sort_by, sort_reverse) values
    """
    st.write(f"**{properties_count}** properties found")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        sort_by = st.selectbox(
            "Sort By",
            options=[
                "price", "price_asc", "rental_yield", "cap_rate", "price_to_rent", 
                "cash_flow", "cash_on_cash", "risk_score", "square_feet", "year_built"
            ],
            format_func=lambda x: {
                "price": "Price (High to Low)",
                "price_asc": "Price (Low to High)",
                "rental_yield": "Rental Yield",
                "cap_rate": "Cap Rate",
                "price_to_rent": "Price to Rent Ratio",
                "cash_flow": "Monthly Cash Flow",
                "cash_on_cash": "Cash on Cash Return",
                "risk_score": "Best Risk Score",
                "square_feet": "Square Footage",
                "year_built": "Year Built (Newest)"
            }.get(x, x),
            index=0
        )
    
    with col2:
        # Default to reverse sort for most options
        default_reverse = sort_by not in ["price_asc", "price_to_rent", "risk_score"]
        
        sort_reverse = st.checkbox(
            "Descending",
            value=default_reverse
        )
    
    return sort_by, sort_reverse
