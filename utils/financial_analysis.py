from typing import Dict, Any, Optional, List
from models.property import Property
import numpy as np
import math

class FinancialAnalysis:
    """
    Financial analysis calculations for real estate properties.
    """
    
    # Default values for financial calculations
    DEFAULT_PROPERTY_TAX_RATE = 0.011  # 1.1% of property value
    DEFAULT_INSURANCE_RATE = 0.005     # 0.5% of property value
    DEFAULT_VACANCY_RATE = 0.05        # 5% vacancy
    DEFAULT_MAINTENANCE_RATE = 0.05    # 5% of rental income
    DEFAULT_MANAGEMENT_FEE_RATE = 0.1  # 10% of rental income
    DEFAULT_MORTGAGE_INTEREST_RATE = 0.055  # 5.5% mortgage rate
    DEFAULT_MORTGAGE_TERM_YEARS = 30
    
    @classmethod
    def calculate_metrics(cls, property_data: Property, 
                          down_payment_percentage: float = 0.2,
                          interest_rate: Optional[float] = None,
                          loan_term_years: int = 30) -> Dict[str, Any]:
        """
        Calculate comprehensive financial metrics for a property
        
        Args:
            property_data: Property object containing basic data
            down_payment_percentage: Percentage of purchase price as down payment (default: 20%)
            interest_rate: Annual interest rate (decimal) - defaults to DEFAULT_MORTGAGE_INTEREST_RATE
            loan_term_years: Mortgage term in years (default: 30)
            
        Returns:
            Dictionary of calculated financial metrics
        """
        if interest_rate is None:
            interest_rate = cls.DEFAULT_MORTGAGE_INTEREST_RATE
            
        metrics = {}
        
        # Basic property information
        price = property_data.price
        monthly_rent = property_data.monthly_rent
        annual_rent = property_data.annual_rent or (monthly_rent * 12 if monthly_rent else None)
        
        if not price or price <= 0:
            return {"error": "Property price is required and must be greater than zero"}
        
        # If we don't have rent information, we can't calculate most metrics
        if not annual_rent:
            metrics["error"] = "Rental information is missing, limited metrics available"
            
            # Calculate simplified mortgage payment if we don't have rent data
            metrics["down_payment"] = price * down_payment_percentage
            metrics["loan_amount"] = price - metrics["down_payment"]
            metrics["monthly_mortgage_payment"] = cls._calculate_mortgage_payment(
                metrics["loan_amount"], interest_rate, loan_term_years)
            
            return metrics
        
        # Ensure we have monthly rent
        if not monthly_rent:
            monthly_rent = annual_rent / 12
            
        # Down payment and loan calculations
        down_payment = price * down_payment_percentage
        loan_amount = price - down_payment
        monthly_mortgage_payment = cls._calculate_mortgage_payment(loan_amount, interest_rate, loan_term_years)
        
        # Calculate expense estimates
        property_tax = price * cls.DEFAULT_PROPERTY_TAX_RATE / 12  # Monthly
        insurance = price * cls.DEFAULT_INSURANCE_RATE / 12  # Monthly
        vacancy_cost = monthly_rent * cls.DEFAULT_VACANCY_RATE  # Expected monthly vacancy cost
        maintenance = monthly_rent * cls.DEFAULT_MAINTENANCE_RATE  # Monthly maintenance cost
        property_management = monthly_rent * cls.DEFAULT_MANAGEMENT_FEE_RATE  # Monthly management fee
        
        # Total monthly expenses
        total_monthly_expenses = property_tax + insurance + vacancy_cost + maintenance + property_management
        
        # Monthly cash flow calculations
        monthly_cash_flow = monthly_rent - monthly_mortgage_payment - total_monthly_expenses
        annual_cash_flow = monthly_cash_flow * 12
        
        # Net Operating Income (NOI) - before mortgage payments
        monthly_noi = monthly_rent - total_monthly_expenses
        annual_noi = monthly_noi * 12
        
        # Cap Rate = Annual NOI / Property Price
        cap_rate = (annual_noi / price) * 100
        
        # Rental Yield = Annual Rent / Property Price
        rental_yield = (annual_rent / price) * 100
        
        # Cash on Cash Return = Annual Cash Flow / Initial Investment
        cash_on_cash_return = (annual_cash_flow / down_payment) * 100
        
        # Gross Rent Multiplier (GRM) = Property Price / Annual Rent
        gross_rent_multiplier = price / annual_rent
        
        # Debt Service Coverage Ratio (DSCR) = NOI / Annual Debt Service
        annual_debt_service = monthly_mortgage_payment * 12
        debt_service_coverage_ratio = annual_noi / annual_debt_service if annual_debt_service > 0 else float('inf')
        
        # Price to Rent Ratio = Property Price / Annual Rent
        price_to_rent_ratio = price / annual_rent
        
        # Break-even ratio = (Operating Expenses + Debt Service) / Gross Operating Income
        break_even_ratio = (total_monthly_expenses + monthly_mortgage_payment) / monthly_rent if monthly_rent > 0 else float('inf')
        
        # 50% Rule test (operating expenses should be around 50% of rent)
        operating_expense_ratio = total_monthly_expenses / monthly_rent if monthly_rent > 0 else float('inf')
        
        # 1% Rule test (monthly rent should be at least 1% of purchase price)
        one_percent_rule_value = monthly_rent / price * 100 if price > 0 else 0
        one_percent_rule_passed = one_percent_rule_value >= 1
        
        # Risk score (basic implementation - can be enhanced)
        risk_factors = []
        risk_score = 0
        
        # Check Cap Rate - higher is better (lower risk)
        if cap_rate < 4:
            risk_factors.append("Low cap rate")
            risk_score += 2
        elif cap_rate < 6:
            risk_factors.append("Moderate cap rate")
            risk_score += 1
            
        # Check Cash on Cash Return - higher is better (lower risk)
        if cash_on_cash_return < 4:
            risk_factors.append("Low cash on cash return")
            risk_score += 2
        elif cash_on_cash_return < 8:
            risk_factors.append("Moderate cash on cash return")
            risk_score += 1
            
        # Check Debt Service Coverage Ratio - higher is better (lower risk)
        if debt_service_coverage_ratio < 1:
            risk_factors.append("DSCR below 1.0 (negative cash flow)")
            risk_score += 3
        elif debt_service_coverage_ratio < 1.25:
            risk_factors.append("Low DSCR (tight cash flow)")
            risk_score += 2
        elif debt_service_coverage_ratio < 1.5:
            risk_factors.append("Moderate DSCR")
            risk_score += 1
            
        # Check 1% Rule - passing is better (lower risk)
        if not one_percent_rule_passed:
            risk_factors.append("Does not meet 1% rule")
            risk_score += 1
            
        # Calculate risk level
        if risk_score <= 1:
            risk_level = "Low"
        elif risk_score <= 4:
            risk_level = "Moderate" 
        else:
            risk_level = "High"
            
        # Compile all metrics
        metrics = {
            # Property basics
            "property_price": price,
            "monthly_rent": monthly_rent,
            "annual_rent": annual_rent,
            
            # Financing
            "down_payment": down_payment,
            "down_payment_percentage": down_payment_percentage * 100,
            "loan_amount": loan_amount,
            "interest_rate": interest_rate * 100,
            "loan_term_years": loan_term_years,
            "monthly_mortgage_payment": monthly_mortgage_payment,
            "annual_mortgage_payment": monthly_mortgage_payment * 12,
            
            # Operating expenses
            "monthly_property_tax": property_tax,
            "annual_property_tax": property_tax * 12,
            "monthly_insurance": insurance,
            "annual_insurance": insurance * 12,
            "monthly_vacancy_cost": vacancy_cost,
            "annual_vacancy_cost": vacancy_cost * 12,
            "monthly_maintenance": maintenance,
            "annual_maintenance": maintenance * 12,
            "monthly_property_management": property_management,
            "annual_property_management": property_management * 12,
            "total_monthly_expenses": total_monthly_expenses,
            "total_annual_expenses": total_monthly_expenses * 12,
            
            # Cash flow
            "monthly_noi": monthly_noi,
            "annual_noi": annual_noi,
            "monthly_cash_flow": monthly_cash_flow,
            "annual_cash_flow": annual_cash_flow,
            
            # Investment metrics
            "cap_rate": cap_rate,
            "rental_yield": rental_yield,
            "cash_on_cash_return": cash_on_cash_return,
            "gross_rent_multiplier": gross_rent_multiplier,
            "debt_service_coverage_ratio": debt_service_coverage_ratio,
            "price_to_rent_ratio": price_to_rent_ratio,
            "break_even_ratio": break_even_ratio,
            "operating_expense_ratio": operating_expense_ratio,
            "one_percent_rule_value": one_percent_rule_value,
            "one_percent_rule_passed": one_percent_rule_passed,
            
            # Risk assessment
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors
        }
        
        return metrics
    
    @classmethod
    def calculate_multiple_scenarios(cls, property_data: Property) -> Dict[str, Dict[str, Any]]:
        """
        Calculate financial metrics under different down payment scenarios
        
        Args:
            property_data: Property object containing basic data
            
        Returns:
            Dictionary with scenarios and their metrics
        """
        scenarios = {}
        
        # Calculate metrics for different down payment percentages
        down_payment_scenarios = [0.20, 0.25, 0.30]
        
        for dp_percentage in down_payment_scenarios:
            scenario_name = f"{int(dp_percentage * 100)}%_down_payment"
            scenarios[scenario_name] = cls.calculate_metrics(
                property_data, 
                down_payment_percentage=dp_percentage
            )
            
        return scenarios
    
    @classmethod
    def perform_stress_test(cls, property_data: Property) -> Dict[str, Any]:
        """
        Perform stress tests to evaluate property performance under adverse conditions
        
        Args:
            property_data: Property object containing basic data
            
        Returns:
            Dictionary with stress test results
        """
        base_metrics = cls.calculate_metrics(property_data)
        stress_tests = {}
        
        # Skip stress tests if we don't have rent data
        if "error" in base_metrics:
            return {"error": base_metrics["error"]}
        
        # Test 1: Increased vacancy (double the vacancy rate)
        vacancy_property = Property(**vars(property_data))
        vacancy_test_metrics = cls.calculate_metrics(
            vacancy_property, 
            down_payment_percentage=0.2
        )
        
        # Adjust for higher vacancy
        vacancy_rate = cls.DEFAULT_VACANCY_RATE * 2
        monthly_rent = property_data.monthly_rent
        vacancy_adjusted_cash_flow = vacancy_test_metrics["monthly_cash_flow"] - (monthly_rent * cls.DEFAULT_VACANCY_RATE)
        
        stress_tests["increased_vacancy"] = {
            "scenario": f"Vacancy rate increased to {vacancy_rate * 100}%",
            "monthly_cash_flow": vacancy_adjusted_cash_flow,
            "annual_cash_flow": vacancy_adjusted_cash_flow * 12,
            "still_profitable": vacancy_adjusted_cash_flow > 0
        }
        
        # Test 2: Interest rate increase (+2%)
        higher_interest_metrics = cls.calculate_metrics(
            property_data,
            down_payment_percentage=0.2,
            interest_rate=cls.DEFAULT_MORTGAGE_INTEREST_RATE + 0.02
        )
        
        stress_tests["interest_rate_increase"] = {
            "scenario": f"Interest rate increased to {(cls.DEFAULT_MORTGAGE_INTEREST_RATE + 0.02) * 100}%",
            "monthly_mortgage_payment": higher_interest_metrics["monthly_mortgage_payment"],
            "monthly_cash_flow": higher_interest_metrics["monthly_cash_flow"],
            "annual_cash_flow": higher_interest_metrics["annual_cash_flow"],
            "still_profitable": higher_interest_metrics["monthly_cash_flow"] > 0
        }
        
        # Test 3: Combined stress (higher vacancy, higher interest, higher expenses)
        # This is a worst-case scenario test
        combined_property = Property(**vars(property_data))
        combined_metrics = cls.calculate_metrics(
            combined_property,
            down_payment_percentage=0.2,
            interest_rate=cls.DEFAULT_MORTGAGE_INTEREST_RATE + 0.02
        )
        
        # Adjust for higher vacancy and maintenance
        vacancy_rate = cls.DEFAULT_VACANCY_RATE * 2
        maintenance_rate = cls.DEFAULT_MAINTENANCE_RATE * 1.5
        
        vacancy_impact = monthly_rent * cls.DEFAULT_VACANCY_RATE
        maintenance_impact = monthly_rent * (cls.DEFAULT_MAINTENANCE_RATE * 0.5)  # The additional 50%
        
        combined_adjusted_cash_flow = combined_metrics["monthly_cash_flow"] - vacancy_impact - maintenance_impact
        
        stress_tests["combined_stress"] = {
            "scenario": "Combined stress: Higher vacancy, interest rate, and maintenance",
            "monthly_cash_flow": combined_adjusted_cash_flow,
            "annual_cash_flow": combined_adjusted_cash_flow * 12,
            "still_profitable": combined_adjusted_cash_flow > 0
        }
        
        # Overall stress test result
        stress_tests["summary"] = {
            "passed_all_tests": all(test["still_profitable"] for test in [
                stress_tests["increased_vacancy"],
                stress_tests["interest_rate_increase"],
                stress_tests["combined_stress"]
            ]),
            "worst_case_monthly_cash_flow": stress_tests["combined_stress"]["monthly_cash_flow"]
        }
        
        return stress_tests
    
    @staticmethod
    def _calculate_mortgage_payment(loan_amount: float, annual_interest_rate: float, loan_term_years: int) -> float:
        """
        Calculate the monthly mortgage payment
        
        Args:
            loan_amount: Principal loan amount
            annual_interest_rate: Annual interest rate as a decimal (e.g., 0.05 for 5%)
            loan_term_years: Loan term in years
            
        Returns:
            Monthly mortgage payment
        """
        # Convert annual rate to monthly rate
        monthly_rate = annual_interest_rate / 12
        
        # Calculate total number of payments
        num_payments = loan_term_years * 12
        
        # Guard against division by zero
        if monthly_rate == 0:
            return loan_amount / num_payments
        
        # Calculate mortgage payment using the formula
        # P = L[c(1 + c)^n]/[(1 + c)^n - 1]
        # where P = payment, L = loan amount, c = monthly interest rate, n = number of payments
        payment = loan_amount * (monthly_rate * math.pow(1 + monthly_rate, num_payments)) / (math.pow(1 + monthly_rate, num_payments) - 1)
        
        return payment
