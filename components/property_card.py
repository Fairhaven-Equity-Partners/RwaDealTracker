import streamlit as st
from typing import Dict, Any, List, Optional
from models.property import Property
import re

def render_property_card(property_data: Property) -> None:
    """
    Render a property card with key information and metrics.
    
    Args:
        property_data: Property object to render
    """
    # Create card container with border
    with st.container(border=True):
        # Property header with title and platform badge
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"### {property_data.address}")
            st.markdown(f"{property_data.city}, {property_data.state} {property_data.zip_code}")
        
        with col2:
            # Source badge styled with appropriate color
            source_colors = {
                "Zillow": "blue",
                "LoopNet": "green"
            }
            source_color = source_colors.get(property_data.source, "gray")
            st.markdown(f"<span style='background-color: {source_color}; color: white; padding: 3px 8px; border-radius: 4px;'>{property_data.source}</span>", unsafe_allow_html=True)
        
        # Property image placeholder with link to listing
        placeholder_url = "https://via.placeholder.com/400x300?text=No+Image+Available"
        
        # Create a clickable link to the property page with the image
        st.markdown(f"[<img src='{placeholder_url}' width='100%' style='border-radius: 8px;'>]({property_data.property_url})", unsafe_allow_html=True)
        
        # Property details grid with 2 columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Price:** ${property_data.price:,.0f}")
            
            # Show property type and year built
            st.markdown(f"**Type:** {property_data.property_type}")
            if property_data.year_built:
                st.markdown(f"**Year Built:** {property_data.year_built}")
            
            # Show bedrooms and bathrooms for residential properties
            if property_data.bedrooms or property_data.bathrooms:
                bed_bath = []
                if property_data.bedrooms:
                    bed_bath.append(f"{property_data.bedrooms} bed")
                if property_data.bathrooms:
                    bed_bath.append(f"{property_data.bathrooms} bath")
                st.markdown(f"**Size:** {' | '.join(bed_bath)}")
            
            # Show square footage and lot size if available
            if property_data.square_feet:
                st.markdown(f"**Square Feet:** {property_data.square_feet:,.0f}")
            if property_data.lot_size:
                st.markdown(f"**Lot Size:** {property_data.lot_size:,.2f} acres")
        
        with col2:
            # Financial metrics
            if property_data.monthly_rent:
                st.markdown(f"**Monthly Rent:** ${property_data.monthly_rent:,.0f}")
            
            if property_data.rental_yield:
                rental_yield_color = "green" if property_data.rental_yield >= 8 else "orange" if property_data.rental_yield >= 5 else "red"
                st.markdown(f"**Rental Yield:** <span style='color: {rental_yield_color}'>{property_data.rental_yield:.2f}%</span>", unsafe_allow_html=True)
            
            if property_data.price_to_rent_ratio:
                ptr_color = "green" if property_data.price_to_rent_ratio <= 15 else "orange" if property_data.price_to_rent_ratio <= 20 else "red"
                st.markdown(f"**Price to Rent Ratio:** <span style='color: {ptr_color}'>{property_data.price_to_rent_ratio:.1f}</span>", unsafe_allow_html=True)
            
            # Cap rate if available
            if property_data.cap_rate:
                cap_rate_color = "green" if property_data.cap_rate >= 7 else "orange" if property_data.cap_rate >= 5 else "red"
                st.markdown(f"**Cap Rate:** <span style='color: {cap_rate_color}'>{property_data.cap_rate:.2f}%</span>", unsafe_allow_html=True)
            elif property_data.financial_metrics and "cap_rate" in property_data.financial_metrics:
                cap_rate = property_data.financial_metrics["cap_rate"]
                cap_rate_color = "green" if cap_rate >= 7 else "orange" if cap_rate >= 5 else "red"
                st.markdown(f"**Cap Rate:** <span style='color: {cap_rate_color}'>{cap_rate:.2f}%</span>", unsafe_allow_html=True)
            
            # Display cash flow if available
            if property_data.financial_metrics and "monthly_cash_flow" in property_data.financial_metrics:
                cash_flow = property_data.financial_metrics["monthly_cash_flow"]
                cash_flow_color = "green" if cash_flow > 0 else "red"
                st.markdown(f"**Monthly Cash Flow:** <span style='color: {cash_flow_color}'>${cash_flow:,.0f}</span>", unsafe_allow_html=True)
            
            # Display risk level if available
            if property_data.financial_metrics and "risk_level" in property_data.financial_metrics:
                risk_level = property_data.financial_metrics["risk_level"]
                risk_colors = {"Low": "green", "Moderate": "orange", "High": "red"}
                risk_color = risk_colors.get(risk_level, "gray")
                st.markdown(f"**Risk Level:** <span style='color: {risk_color}'>{risk_level}</span>", unsafe_allow_html=True)
        
        # View details button
        if st.button("View Financial Analysis", key=f"view_{property_data.id}"):
            st.session_state.selected_property = property_data

def render_property_details(property_data: Property) -> None:
    """
    Render detailed property analysis view.
    
    Args:
        property_data: Property object to display in detail
    """
    # Back button
    if st.button("← Back to Property List"):
        st.session_state.selected_property = None
        st.rerun()
    
    # Property header
    st.markdown(f"# {property_data.address}")
    st.markdown(f"## {property_data.city}, {property_data.state} {property_data.zip_code}")
    
    # Source and property type info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Source:** {property_data.source}")
        st.markdown(f"**Property Type:** {property_data.property_type}")
    with col2:
        st.markdown(f"**Price:** ${property_data.price:,.0f}")
        if property_data.year_built:
            st.markdown(f"**Year Built:** {property_data.year_built}")
    
    # External link to property
    st.markdown(f"[View Original Listing]({property_data.property_url})")
    
    # Property description
    if property_data.description:
        with st.expander("Property Description", expanded=True):
            # Clean up description text - remove excessive whitespace
            description = re.sub(r'\s+', ' ', property_data.description).strip()
            st.write(description)
    
    # Property features
    if property_data.features:
        with st.expander("Features & Amenities", expanded=True):
            # Display features in two columns
            cols = st.columns(2)
            half_length = (len(property_data.features) + 1) // 2
            
            with cols[0]:
                for feature in property_data.features[:half_length]:
                    st.markdown(f"- {feature}")
            
            with cols[1]:
                for feature in property_data.features[half_length:]:
                    st.markdown(f"- {feature}")
    
    # Financial Analysis
    st.markdown("## Financial Analysis")
    
    # Key metrics in cards at top
    metric_cols = st.columns(4)
    
    # Calculate metrics if not already present
    if not property_data.financial_metrics:
        from utils.financial_analysis import FinancialAnalysis
        property_data.financial_metrics = FinancialAnalysis.calculate_metrics(property_data)
    
    with metric_cols[0]:
        if property_data.rental_yield:
            st.metric("Rental Yield", f"{property_data.rental_yield:.2f}%")
        elif "rental_yield" in property_data.financial_metrics:
            st.metric("Rental Yield", f"{property_data.financial_metrics['rental_yield']:.2f}%")
        else:
            st.metric("Rental Yield", "N/A")
    
    with metric_cols[1]:
        if "cap_rate" in property_data.financial_metrics:
            st.metric("Cap Rate", f"{property_data.financial_metrics['cap_rate']:.2f}%")
        elif property_data.cap_rate:
            st.metric("Cap Rate", f"{property_data.cap_rate:.2f}%")
        else:
            st.metric("Cap Rate", "N/A")
    
    with metric_cols[2]:
        if "cash_on_cash_return" in property_data.financial_metrics:
            st.metric("Cash on Cash Return", f"{property_data.financial_metrics['cash_on_cash_return']:.2f}%")
        else:
            st.metric("Cash on Cash Return", "N/A")
    
    with metric_cols[3]:
        if "monthly_cash_flow" in property_data.financial_metrics:
            st.metric("Monthly Cash Flow", f"${property_data.financial_metrics['monthly_cash_flow']:,.0f}")
        else:
            st.metric("Monthly Cash Flow", "N/A")
    
    # Financial details
    with st.container(border=True):
        # Tabs for different financial views
        fin_tab1, fin_tab2, fin_tab3 = st.tabs(["Monthly Financials", "Investment Metrics", "Risk Analysis"])
        
        with fin_tab1:
            # Monthly financial breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Income")
                if property_data.monthly_rent:
                    st.markdown(f"Monthly Rental Income: ${property_data.monthly_rent:,.0f}")
                elif "monthly_rent" in property_data.financial_metrics:
                    st.markdown(f"Monthly Rental Income: ${property_data.financial_metrics['monthly_rent']:,.0f}")
                else:
                    st.markdown("Monthly Rental Income: N/A")
                
                if "vacancy_cost" in property_data.financial_metrics:
                    vacancy_cost = property_data.financial_metrics["monthly_vacancy_cost"]
                    st.markdown(f"Less Vacancy (5%): -${vacancy_cost:,.0f}")
                
                st.markdown("### Expenses")
                
                if "monthly_mortgage_payment" in property_data.financial_metrics:
                    st.markdown(f"Mortgage Payment: ${property_data.financial_metrics['monthly_mortgage_payment']:,.0f}")
                
                if "monthly_property_tax" in property_data.financial_metrics:
                    st.markdown(f"Property Tax: ${property_data.financial_metrics['monthly_property_tax']:,.0f}")
                
                if "monthly_insurance" in property_data.financial_metrics:
                    st.markdown(f"Insurance: ${property_data.financial_metrics['monthly_insurance']:,.0f}")
                
                if "monthly_maintenance" in property_data.financial_metrics:
                    st.markdown(f"Maintenance: ${property_data.financial_metrics['monthly_maintenance']:,.0f}")
                
                if "monthly_property_management" in property_data.financial_metrics:
                    st.markdown(f"Property Management: ${property_data.financial_metrics['monthly_property_management']:,.0f}")
            
            with col2:
                st.markdown("### Summary")
                
                if "monthly_noi" in property_data.financial_metrics:
                    noi = property_data.financial_metrics["monthly_noi"]
                    st.markdown(f"Net Operating Income: ${noi:,.0f}")
                
                if "monthly_cash_flow" in property_data.financial_metrics:
                    cash_flow = property_data.financial_metrics["monthly_cash_flow"]
                    cash_flow_color = "green" if cash_flow > 0 else "red"
                    st.markdown(f"Monthly Cash Flow: <span style='color: {cash_flow_color}'>${cash_flow:,.0f}</span>", unsafe_allow_html=True)
                    st.markdown(f"Annual Cash Flow: <span style='color: {cash_flow_color}'>${cash_flow * 12:,.0f}</span>", unsafe_allow_html=True)
                
                # Add visualization
                if "monthly_cash_flow" in property_data.financial_metrics:
                    monthly_cash_flow = property_data.financial_metrics["monthly_cash_flow"]
                    monthly_mortgage = property_data.financial_metrics.get("monthly_mortgage_payment", 0)
                    monthly_expenses = property_data.financial_metrics.get("total_monthly_expenses", 0)
                    monthly_income = monthly_cash_flow + monthly_mortgage + monthly_expenses
                    
                    import plotly.graph_objects as go
                    
                    # Create a waterfall chart
                    fig = go.Figure(go.Waterfall(
                        name="Monthly Cash Flow",
                        orientation="v",
                        measure=["absolute", "relative", "relative", "total"],
                        x=["Income", "Mortgage", "Expenses", "Cash Flow"],
                        textposition="outside",
                        text=[f"${monthly_income:,.0f}", f"-${monthly_mortgage:,.0f}", f"-${monthly_expenses:,.0f}", f"${monthly_cash_flow:,.0f}"],
                        y=[monthly_income, -monthly_mortgage, -monthly_expenses, monthly_cash_flow],
                        connector={"line": {"color": "rgb(63, 63, 63)"}},
                    ))
                    
                    fig.update_layout(
                        title="Monthly Cash Flow Breakdown",
                        height=300,
                        margin=dict(t=50, b=20, l=20, r=20),
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
        
        with fin_tab2:
            # Investment metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Purchase Information")
                st.markdown(f"Purchase Price: ${property_data.price:,.0f}")
                
                if "down_payment" in property_data.financial_metrics:
                    down_payment = property_data.financial_metrics["down_payment"]
                    down_payment_percentage = property_data.financial_metrics["down_payment_percentage"]
                    st.markdown(f"Down Payment ({down_payment_percentage:.0f}%): ${down_payment:,.0f}")
                
                if "loan_amount" in property_data.financial_metrics:
                    loan_amount = property_data.financial_metrics["loan_amount"]
                    interest_rate = property_data.financial_metrics["interest_rate"]
                    loan_term = property_data.financial_metrics["loan_term_years"]
                    st.markdown(f"Loan Amount: ${loan_amount:,.0f}")
                    st.markdown(f"Interest Rate: {interest_rate:.2f}%")
                    st.markdown(f"Loan Term: {loan_term} years")
            
            with col2:
                st.markdown("### Return Metrics")
                
                if "cap_rate" in property_data.financial_metrics:
                    cap_rate = property_data.financial_metrics["cap_rate"]
                    cap_rate_color = "green" if cap_rate >= 7 else "orange" if cap_rate >= 5 else "red"
                    st.markdown(f"Cap Rate: <span style='color: {cap_rate_color}'>{cap_rate:.2f}%</span>", unsafe_allow_html=True)
                
                if "rental_yield" in property_data.financial_metrics:
                    rental_yield = property_data.financial_metrics["rental_yield"]
                    rental_yield_color = "green" if rental_yield >= 8 else "orange" if rental_yield >= 5 else "red"
                    st.markdown(f"Rental Yield: <span style='color: {rental_yield_color}'>{rental_yield:.2f}%</span>", unsafe_allow_html=True)
                
                if "cash_on_cash_return" in property_data.financial_metrics:
                    cash_on_cash = property_data.financial_metrics["cash_on_cash_return"]
                    cash_on_cash_color = "green" if cash_on_cash >= 8 else "orange" if cash_on_cash >= 5 else "red"
                    st.markdown(f"Cash on Cash Return: <span style='color: {cash_on_cash_color}'>{cash_on_cash:.2f}%</span>", unsafe_allow_html=True)
                
                if "price_to_rent_ratio" in property_data.financial_metrics:
                    price_to_rent = property_data.financial_metrics["price_to_rent_ratio"]
                    ptr_color = "green" if price_to_rent <= 15 else "orange" if price_to_rent <= 20 else "red"
                    st.markdown(f"Price to Rent Ratio: <span style='color: {ptr_color}'>{price_to_rent:.1f}</span>", unsafe_allow_html=True)
                
                if "gross_rent_multiplier" in property_data.financial_metrics:
                    grm = property_data.financial_metrics["gross_rent_multiplier"]
                    grm_color = "green" if grm <= 8 else "orange" if grm <= 12 else "red"
                    st.markdown(f"Gross Rent Multiplier: <span style='color: {grm_color}'>{grm:.1f}</span>", unsafe_allow_html=True)
                
                if "debt_service_coverage_ratio" in property_data.financial_metrics:
                    dscr = property_data.financial_metrics["debt_service_coverage_ratio"]
                    dscr_color = "green" if dscr >= 1.5 else "orange" if dscr >= 1.2 else "red"
                    st.markdown(f"DSCR: <span style='color: {dscr_color}'>{dscr:.2f}</span>", unsafe_allow_html=True)
                
                if "one_percent_rule_value" in property_data.financial_metrics:
                    one_percent = property_data.financial_metrics["one_percent_rule_value"]
                    one_percent_passed = property_data.financial_metrics["one_percent_rule_passed"]
                    one_percent_color = "green" if one_percent_passed else "red"
                    st.markdown(f"1% Rule: <span style='color: {one_percent_color}'>{one_percent:.2f}%</span>", unsafe_allow_html=True)
        
        with fin_tab3:
            # Risk analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Risk Assessment")
                
                if "risk_level" in property_data.financial_metrics:
                    risk_level = property_data.financial_metrics["risk_level"]
                    risk_score = property_data.financial_metrics["risk_score"]
                    risk_colors = {"Low": "green", "Moderate": "orange", "High": "red"}
                    risk_color = risk_colors.get(risk_level, "gray")
                    st.markdown(f"Risk Level: <span style='color: {risk_color}'>{risk_level}</span>", unsafe_allow_html=True)
                    st.markdown(f"Risk Score: {risk_score}/10")
                
                if "risk_factors" in property_data.financial_metrics and property_data.financial_metrics["risk_factors"]:
                    st.markdown("### Risk Factors")
                    for factor in property_data.financial_metrics["risk_factors"]:
                        st.markdown(f"- {factor}")
                else:
                    st.markdown("### Risk Factors")
                    st.markdown("No specific risk factors identified.")
            
            with col2:
                st.markdown("### Break-Even Analysis")
                
                if "break_even_ratio" in property_data.financial_metrics:
                    break_even = property_data.financial_metrics["break_even_ratio"] * 100
                    break_even_color = "green" if break_even <= 70 else "orange" if break_even <= 85 else "red"
                    st.markdown(f"Break-Even Ratio: <span style='color: {break_even_color}'>{break_even:.1f}%</span>", unsafe_allow_html=True)
                    st.markdown(f"This property will break even with a {break_even:.1f}% occupancy rate.")
                
                if "operating_expense_ratio" in property_data.financial_metrics:
                    expense_ratio = property_data.financial_metrics["operating_expense_ratio"] * 100
                    expense_color = "green" if expense_ratio <= 40 else "orange" if expense_ratio <= 50 else "red"
                    st.markdown(f"Operating Expense Ratio: <span style='color: {expense_color}'>{expense_ratio:.1f}%</span>", unsafe_allow_html=True)
                
                # Perform stress test
                from utils.financial_analysis import FinancialAnalysis
                stress_tests = FinancialAnalysis.perform_stress_test(property_data)
                
                if "error" not in stress_tests:
                    st.markdown("### Stress Test Results")
                    
                    # Vacancy stress test
                    vacancy_test = stress_tests["increased_vacancy"]
                    vacancy_color = "green" if vacancy_test["still_profitable"] else "red"
                    st.markdown(f"Increased Vacancy: <span style='color: {vacancy_color}'>${vacancy_test['monthly_cash_flow']:,.0f}/month</span>", unsafe_allow_html=True)
                    
                    # Interest rate stress test
                    interest_test = stress_tests["interest_rate_increase"]
                    interest_color = "green" if interest_test["still_profitable"] else "red"
                    st.markdown(f"Interest Rate Increase: <span style='color: {interest_color}'>${interest_test['monthly_cash_flow']:,.0f}/month</span>", unsafe_allow_html=True)
                    
                    # Combined stress test
                    combined_test = stress_tests["combined_stress"]
                    combined_color = "green" if combined_test["still_profitable"] else "red"
                    st.markdown(f"Combined Stress Scenario: <span style='color: {combined_color}'>${combined_test['monthly_cash_flow']:,.0f}/month</span>", unsafe_allow_html=True)
                    
                    # Overall stress test summary
                    if stress_tests["summary"]["passed_all_tests"]:
                        st.markdown("✅ Property passes all stress tests")
                    else:
                        st.markdown("⚠️ Property shows risk in stress scenarios")
    
    # Down payment scenario analysis
    st.markdown("## Financing Scenarios")
    
    # Calculate scenarios
    from utils.financial_analysis import FinancialAnalysis
    scenarios = FinancialAnalysis.calculate_multiple_scenarios(property_data)
    
    if scenarios and "error" not in next(iter(scenarios.values()), {}):
        # Create a comparison table
        scenario_names = list(scenarios.keys())
        metrics = ["down_payment", "loan_amount", "monthly_mortgage_payment", 
                  "monthly_cash_flow", "cash_on_cash_return"]
        metric_labels = {
            "down_payment": "Down Payment",
            "loan_amount": "Loan Amount",
            "monthly_mortgage_payment": "Monthly Mortgage",
            "monthly_cash_flow": "Monthly Cash Flow",
            "cash_on_cash_return": "Cash on Cash Return"
        }
        
        # Build and format the data for the table
        data = []
        
        for metric in metrics:
            row = {"Metric": metric_labels[metric]}
            for scenario in scenario_names:
                value = scenarios[scenario].get(metric, "N/A")
                if metric in ["down_payment", "loan_amount", "monthly_mortgage_payment", "monthly_cash_flow"]:
                    # Format as currency
                    if isinstance(value, (int, float)):
                        row[scenario] = f"${value:,.0f}"
                    else:
                        row[scenario] = "N/A"
                elif metric == "cash_on_cash_return":
                    # Format as percentage
                    if isinstance(value, (int, float)):
                        row[scenario] = f"{value:.2f}%"
                    else:
                        row[scenario] = "N/A"
                else:
                    row[scenario] = str(value)
            data.append(row)
        
        # Create a Plotly table
        import plotly.graph_objects as go
        
        header_vals = ["Metric"] + [s.replace("_", " ").title() for s in scenario_names]
        cell_vals = [
            [row["Metric"] for row in data],
        ]
        
        for scenario in scenario_names:
            cell_vals.append([row[scenario] for row in data])
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=header_vals,
                fill_color='rgb(100, 121, 247)',
                align='center',
                font=dict(color='white', size=14)
            ),
            cells=dict(
                values=cell_vals,
                fill_color='lavender',
                align='center',
                font=dict(size=14)
            )
        )])
        
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=250
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add visualization of cash on cash return across scenarios
        cash_on_cash_values = [scenarios[scenario].get("cash_on_cash_return", 0) for scenario in scenario_names]
        scenario_labels = [s.replace("_down_payment", "").replace("_", " ").title() for s in scenario_names]
        
        bar_fig = go.Figure(data=[
            go.Bar(
                x=scenario_labels,
                y=cash_on_cash_values,
                text=[f"{v:.2f}%" for v in cash_on_cash_values],
                textposition='auto',
                marker_color='rgb(55, 83, 177)'
            )
        ])
        
        bar_fig.update_layout(
            title='Cash on Cash Return by Down Payment Scenario',
            xaxis_title='Down Payment Scenario',
            yaxis_title='Cash on Cash Return (%)',
            height=400
        )
        
        st.plotly_chart(bar_fig, use_container_width=True)
    else:
        st.write("Financing scenario analysis not available for this property.")
