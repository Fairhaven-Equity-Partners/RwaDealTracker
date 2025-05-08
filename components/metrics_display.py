import streamlit as st
from typing import List, Dict, Any
from models.property import Property
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

def render_metrics_summary(properties: List[Property]) -> None:
    """
    Render a summary of key metrics for the set of properties.
    
    Args:
        properties: List of Property objects
    """
    if not properties:
        st.info("No properties available to analyze. Use the search filters to find properties.")
        return
    
    st.markdown("## Market Overview")
    
    # Get the metrics
    price_metrics = _calculate_price_metrics(properties)
    rental_metrics = _calculate_rental_metrics(properties)
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Average Price", f"${price_metrics['mean_price']:,.0f}")
        st.metric("Median Price", f"${price_metrics['median_price']:,.0f}")
    
    with col2:
        st.metric("Average Monthly Rent", f"${rental_metrics['mean_monthly_rent']:,.0f}")
        st.metric("Median Monthly Rent", f"${rental_metrics['median_monthly_rent']:,.0f}")
    
    with col3:
        st.metric("Average Rental Yield", f"{rental_metrics['mean_rental_yield']:.2f}%")
        st.metric("Median Rental Yield", f"{rental_metrics['median_rental_yield']:.2f}%")
    
    # Create vizualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Price distribution chart
        if len(properties) > 1:
            _render_price_distribution(properties)
    
    with col2:
        # Rental yield vs price chart
        if len(properties) > 1:
            _render_yield_vs_price(properties)

def _calculate_price_metrics(properties: List[Property]) -> Dict[str, float]:
    """
    Calculate price metrics from the list of properties.
    
    Args:
        properties: List of Property objects
        
    Returns:
        Dictionary of price metrics
    """
    prices = [p.price for p in properties if p.price is not None]
    
    if not prices:
        return {
            "mean_price": 0,
            "median_price": 0,
            "min_price": 0,
            "max_price": 0
        }
    
    return {
        "mean_price": np.mean(prices),
        "median_price": np.median(prices),
        "min_price": min(prices),
        "max_price": max(prices)
    }

def _calculate_rental_metrics(properties: List[Property]) -> Dict[str, float]:
    """
    Calculate rental metrics from the list of properties.
    
    Args:
        properties: List of Property objects
        
    Returns:
        Dictionary of rental metrics
    """
    monthly_rents = [p.monthly_rent for p in properties if p.monthly_rent is not None]
    rental_yields = [p.rental_yield for p in properties if p.rental_yield is not None]
    
    if not monthly_rents:
        monthly_rents = [0]
    
    if not rental_yields:
        rental_yields = [0]
    
    return {
        "mean_monthly_rent": np.mean(monthly_rents),
        "median_monthly_rent": np.median(monthly_rents),
        "min_monthly_rent": min(monthly_rents),
        "max_monthly_rent": max(monthly_rents),
        "mean_rental_yield": np.mean(rental_yields),
        "median_rental_yield": np.median(rental_yields),
        "min_rental_yield": min(rental_yields),
        "max_rental_yield": max(rental_yields)
    }

def _render_price_distribution(properties: List[Property]) -> None:
    """
    Render a price distribution chart.
    
    Args:
        properties: List of Property objects
    """
    prices = [p.price for p in properties if p.price is not None]
    
    if not prices or len(prices) < 2:
        st.info("Insufficient price data for distribution chart.")
        return
    
    # Create bins - determine the number based on data size
    num_bins = min(10, max(5, len(prices) // 5))
    
    # Create histogram with Plotly
    fig = px.histogram(
        x=prices,
        nbins=num_bins,
        labels={"x": "Price"},
        title="Price Distribution",
        color_discrete_sequence=['rgb(55, 83, 177)']
    )
    
    fig.update_layout(
        xaxis_title="Price ($)",
        yaxis_title="Number of Properties",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    fig.update_xaxes(tickprefix="$", tickformat=",")
    
    st.plotly_chart(fig, use_container_width=True)

def _render_yield_vs_price(properties: List[Property]) -> None:
    """
    Render a rental yield vs price scatter plot.
    
    Args:
        properties: List of Property objects
    """
    # Prepare data
    data = []
    for p in properties:
        if p.price is not None and p.rental_yield is not None:
            data.append({
                "Price": p.price,
                "Rental Yield": p.rental_yield,
                "Source": p.source,
                "Type": p.property_type
            })
    
    if not data or len(data) < 2:
        st.info("Insufficient data for yield vs price chart.")
        return
    
    df = pd.DataFrame(data)
    
    # Create scatter plot
    fig = px.scatter(
        df,
        x="Price",
        y="Rental Yield",
        color="Source",
        hover_data=["Type"],
        title="Rental Yield vs Price",
    )
    
    fig.update_layout(
        xaxis_title="Price ($)",
        yaxis_title="Rental Yield (%)",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    fig.update_xaxes(tickprefix="$", tickformat=",")
    fig.update_yaxes(ticksuffix="%")
    
    st.plotly_chart(fig, use_container_width=True)

def render_property_type_breakdown(properties: List[Property]) -> None:
    """
    Render a breakdown of properties by type.
    
    Args:
        properties: List of Property objects
    """
    if not properties:
        return
    
    # Count properties by type
    property_types = {}
    for p in properties:
        if p.property_type:
            property_type = p.property_type
            property_types[property_type] = property_types.get(property_type, 0) + 1
    
    if not property_types:
        return
    
    # Create pie chart of property types
    labels = list(property_types.keys())
    values = list(property_types.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4
    )])
    
    fig.update_layout(
        title="Properties by Type",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_source_breakdown(properties: List[Property]) -> None:
    """
    Render a breakdown of properties by source.
    
    Args:
        properties: List of Property objects
    """
    if not properties:
        return
    
    # Count properties by source
    sources = {}
    for p in properties:
        if p.source:
            sources[p.source] = sources.get(p.source, 0) + 1
    
    if not sources:
        return
    
    # Create pie chart of sources
    labels = list(sources.keys())
    values = list(sources.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4
    )])
    
    fig.update_layout(
        title="Properties by Source",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)
