import streamlit as st
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Optional
import concurrent.futures
import time

# Import custom modules
from models.property import Property
from utils.data_aggregator import DataAggregator
from utils.financial_analysis import FinancialAnalysis
from components.filters import render_search_filters, render_advanced_filters, render_sorting_options
from components.property_card import render_property_card, render_property_details
from components.metrics_display import render_metrics_summary, render_property_type_breakdown, render_source_breakdown

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="RWA Deal Radar",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point"""
    # Initialize session state for storing data between reruns
    if 'properties' not in st.session_state:
        st.session_state.properties = []
    if 'filtered_properties' not in st.session_state:
        st.session_state.filtered_properties = []
    if 'selected_property' not in st.session_state:
        st.session_state.selected_property = None
    if 'search_performed' not in st.session_state:
        st.session_state.search_performed = False
    if 'loading' not in st.session_state:
        st.session_state.loading = False
    
    # Render header
    st.title("RWA Deal Radar")
    st.subheader("Real Estate Investment Analysis Platform")
    
    # If a property is selected, render its detailed view
    if st.session_state.selected_property:
        render_property_details(st.session_state.selected_property)
        return
    
    # Render filter sections
    search_filters = render_search_filters()
    advanced_filters = render_advanced_filters()
    
    # Combine basic and advanced filters
    all_filters = {**search_filters, **advanced_filters}
    
    # Handle search button click
    if search_filters["search_clicked"]:
        with st.spinner("Searching for properties..."):
            st.session_state.loading = True
            
            # Initialize data aggregator
            data_aggregator = DataAggregator()
            
            # Fetch properties
            st.session_state.properties = data_aggregator.fetch_properties(
                location=search_filters["location"],
                property_types=search_filters["property_types"],
                min_price=search_filters["min_price"],
                max_price=search_filters["max_price"],
                max_results_per_source=15  # Limit for faster results
            )
            
            # Calculate financial metrics for each property
            st.session_state.properties = calculate_financial_metrics(st.session_state.properties)
            
            # Apply filters to the properties
            st.session_state.filtered_properties = data_aggregator.filter_properties(
                st.session_state.properties,
                all_filters
            )
            
            st.session_state.search_performed = True
            st.session_state.loading = False
            st.rerun()
    
    # Display loading indicator
    if st.session_state.loading:
        st.info("Loading properties... This might take a moment.")
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
        st.session_state.loading = False
        st.rerun()
    
    # If search has been performed, display results and filters
    if st.session_state.search_performed:
        # Apply filters to properties (for when filter values change without a new search)
        if st.session_state.properties:
            data_aggregator = DataAggregator()
            st.session_state.filtered_properties = data_aggregator.filter_properties(
                st.session_state.properties,
                all_filters
            )
        
        # Render market metrics summary
        render_metrics_summary(st.session_state.filtered_properties)
        
        # Display property type and source breakdowns
        col1, col2 = st.columns(2)
        with col1:
            render_property_type_breakdown(st.session_state.filtered_properties)
        with col2:
            render_source_breakdown(st.session_state.filtered_properties)
        
        # Render sorting options
        sort_by, sort_reverse = render_sorting_options(len(st.session_state.filtered_properties))
        
        # Sort the properties
        if st.session_state.filtered_properties:
            data_aggregator = DataAggregator()
            sorted_properties = data_aggregator.sort_properties(
                st.session_state.filtered_properties,
                sort_by=sort_by,
                reverse=sort_reverse
            )
            
            # Display property listings
            st.markdown("## Property Listings")
            
            # Create a grid layout for property cards
            NUM_COLS = 2  # Number of columns in the grid
            
            for i in range(0, len(sorted_properties), NUM_COLS):
                cols = st.columns(NUM_COLS)
                
                for j in range(NUM_COLS):
                    idx = i + j
                    if idx < len(sorted_properties):
                        with cols[j]:
                            render_property_card(sorted_properties[idx])
        else:
            st.info("No properties found matching your criteria. Try adjusting your filters.")
    else:
        # Display welcome message if no search has been performed
        st.markdown("""
        ## Welcome to RWA Deal Radar
        
        This platform helps you discover and analyze real estate investment opportunities across multiple sources.
        
        ### Getting Started
        1. Enter a location in the search box above
        2. Adjust price range and property types if needed
        3. Click "Search Properties" to find investment opportunities
        4. Use advanced filters to narrow down results
        5. View detailed financial analysis by clicking on a property
        
        ### Key Features
        - Property data from multiple sources (Zillow, LoopNet)
        - Comprehensive financial metrics (rental yield, cap rate, cash flow)
        - Risk assessment and stress testing
        - Financing scenario analysis
        """)

def calculate_financial_metrics(properties: List[Property]) -> List[Property]:
    """
    Calculate financial metrics for a list of properties using parallel processing
    
    Args:
        properties: List of Property objects
        
    Returns:
        List of Property objects with calculated financial metrics
    """
    if not properties:
        return []
    
    logger.info(f"Calculating financial metrics for {len(properties)} properties")
    
    # Define function to calculate metrics for a single property
    def calculate_for_property(prop):
        try:
            metrics = FinancialAnalysis.calculate_metrics(prop)
            prop.financial_metrics = metrics
            return prop
        except Exception as e:
            logger.error(f"Error calculating financial metrics for property {prop.id}: {e}")
            return prop
    
    # Use ThreadPoolExecutor to calculate metrics in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        result_properties = list(executor.map(calculate_for_property, properties))
    
    logger.info(f"Completed financial metrics calculation for {len(result_properties)} properties")
    return result_properties

if __name__ == "__main__":
    main()
