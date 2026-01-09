"""
Mock data templates based on FameScore Report structure
This file contains templates for generating mock API responses
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import random

def generate_mock_famescore_report(gstin: str, pan: str) -> Dict[str, Any]:
    """
    Generate a complete mock FameScore report based on the PDF structure
    """

    # Base entity information
    legal_name = "FINAGG TECHNOLOGIES PRIVATE LIMITED"

    return {
        "report_metadata": {
            "report_date": datetime.now().isoformat(),
            "application_id": f"FAME{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "gstin": gstin,
            "source": "FameScore.ai"
        },

        "entity_information": {
            "legal_name": legal_name,
            "trade_name": legal_name,
            "constitution": "private_limited",
            "date_of_incorporation": "2021-02-21",
            "gst_numbers": [
                {"gstin": gstin[:2] + "AADCF8429L1Z4", "state": "UTTAR PRADESH", "status": "active"},
                {"gstin": "29AADCF8429L1ZX", "state": "Karnataka", "status": "active"},
                {"gstin": "36AADCF8429L1Z2", "state": "Telangana", "status": "active"}
            ],
            "pan": pan,
            "udyam_number": "UDYAM-DL-02-0000143",
            "gst_aggregated_turnover": 2411.48,  # in lakhs
            "registered_address": {
                "line1": "C 1, SECTOR 16",
                "city": "Noida",
                "state": "Uttar Pradesh",
                "pincode": "201301"
            }
        },

        "bank_details": [
            {
                "bank_name": "HDFC Bank",
                "account_number_masked": "*****2000825544",
                "ifsc": "*****004918",
                "account_type": "OD",
                "branch_address": "JANA SMALL FINANCE BANK, SHOP NO.5, GROUND FLOOR, BLOCK N, SECTOR18, NOIDA, UTTAR PRADESH 201301"
            },
            {
                "bank_name": "Kotak Mahindra",
                "account_number_masked": "*****657456",
                "ifsc": "******07466",
                "account_type": "CC",
                "branch_address": "Shalimar, New Delhi 20003"
            }
        ],

        "credit_bureau_commercial": {
            "bureau_type": "Commercial",
            "member_since": "2024-07-01 20:44:50",
            "score": "CMR-2",
            "overdue_amount": 1.38898,  # lakhs
            "total_outstanding_loan_amount": 27.10443,  # lakhs
            "active_loans": 19
        },

        "credit_bureau_consumer": {
            "promoters": [
                {
                    "name": "Pawan",
                    "bureau_type": "Consumer",
                    "member_since": "2024-05-02 20:44:50",
                    "score": 800,
                    "overdue_amount": 1.00898,  # lakhs
                    "total_outstanding": 15.10443,  # lakhs
                    "active_loans": 4
                },
                {
                    "name": "Komal",
                    "bureau_type": "Consumer",
                    "member_since": "2024-07-03 20:44:50",
                    "score": 750,
                    "overdue_amount": 0.60898,  # lakhs
                    "total_outstanding": 18.10443,  # lakhs
                    "active_loans": 10
                }
            ]
        },

        "existing_facilities": [
            {
                "facility_number": "Credit Facility 1",
                "loan_type": "Long Term",
                "loan_start_date": "08-09-2022",
                "sanctioned_amount": 25.0,
                "sanctioned_date": "08-09-2022",
                "source_bank": "-",
                "tenure_months": 24,
                "lender": "-",
                "remark": "NA",
                "overdue_days": 0,
                "emi_in_bureau": 0.89,
                "emi_in_bank_statement": 0.89,
                "emi_calculated_from_dto": None,
                "emi_match": "Yes",
                "status": "Active"
            },
            {
                "facility_number": "Credit Facility 2",
                "loan_type": "UBL",
                "loan_start_date": "14-02-2024",
                "sanctioned_amount": 30.0,
                "sanctioned_date": "14-02-2024",
                "source_bank": "ICICI Bank",
                "tenure_months": 120,
                "overdue_days": 10,
                "remark": "SMA 0",
                "emi_in_bureau": None,
                "emi_in_bank_statement": 1.06,
                "emi_calculated_from_dto": 0.96,
                "emi_match": "No",
                "status": "Active"
            },
            {
                "facility_number": "Credit Facility 3",
                "loan_type": "UBL",
                "loan_start_date": "30-10-2024",
                "sanctioned_amount": 32.0,
                "sanctioned_date": "30-10-2024",
                "source_bank": "Union Bank",
                "tenure_months": 48,
                "overdue_days": 8,
                "remark": "Overdue",
                "emi_in_bureau": 1.121,
                "emi_in_bank_statement": 0.11,
                "emi_calculated_from_dto": None,
                "emi_match": "No",
                "status": "Active"
            }
        ],

        "closed_loans": [
            {
                "loan_start_date": "08-02-2023",
                "loan_amount": 24.25798,
                "closed_date": "08-08-2023",
                "loan_type": "Auto"
            },
            {
                "loan_start_date": "12-04-2023",
                "loan_amount": 34.21798,
                "closed_date": "10-10-2023",
                "loan_type": "Overdraft"
            }
        ],

        "compliance": {
            "gstr1_filing": {
                "aug_23": "filed", "sep_23": "filed", "oct_23": "filed", "nov_23": "filed",
                "dec_23": "delayed", "jan_24": "filed", "feb_24": "filed", "mar_24": "filed",
                "apr_24": "filed", "may_24": "filed", "jun_24": "filed", "jul_24": "filed"
            },
            "gstr3b_filing": {
                "aug_23": "filed", "sep_23": "filed", "oct_23": "filed", "nov_23": "filed",
                "dec_23": "delayed", "jan_24": "filed", "feb_24": "filed", "mar_24": "filed",
                "apr_24": "filed", "may_24": "filed", "jun_24": "filed", "jul_24": "filed"
            },
            "filing_consistency": 0.84,
            "delayed_filings_count": 1,
            "return_percentage": 0.0
        },

        "udyam_registration": {
            "entity_name": "ABC Pvt. Ltd.",
            "udyam_number": "UDYAM-UP-29-0114616",
            "date_of_incorporation": "01-01-2020",
            "registration_date": "15-02-2024",
            "date_of_commencement": "10-01-2020",
            "activity": "Update Banking Detail",
            "social_category": "General",
            "organizational_type": "Private Limited",
            "major_activity": "Manufacturing",
            "activity_code": "NIC 224",
            "contact_email": "contact@abcpvtltd.in",
            "registered_mobile": "9237823677",
            "addresses": {
                "registered": {
                    "line1": "Plot No. 12",
                    "line2": "Industrial Area",
                    "line3": "Phase 2",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "pin": "110002"
                },
                "working": {
                    "line1": "Unit No. 34",
                    "line2": "Business Complex",
                    "line3": "Tower B",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "pin": "110002"
                }
            },
            "banking_details": [
                {
                    "bank_name": "HDFC Bank",
                    "account_number_masked": "*****2000825544",
                    "ifsc": "*****004918",
                    "account_type": "OD"
                },
                {
                    "bank_name": "Kotak Mahindra",
                    "account_number_masked": "*****657456",
                    "ifsc": "******07466",
                    "account_type": "CC"
                }
            ],
            "financial_details": {
                "applicable_financial_year": "2023-24",
                "written_day_value": 150000,
                "exclusion_of_cost": 150000,
                "net_investment_plant_machinery": 200000,
                "total_turnover": 300000,
                "export_turnover": 120000,
                "net_turnover": 250000
            },
            "employment": {
                "total_employees": 50,
                "male_employees": 30,
                "female_employees": 18,
                "other_employees": 2
            }
        },

        "itr_data": {
            "last_2_years": [
                {
                    "financial_year": "2022-2023",
                    "assessment_year": "2023-2024",
                    "itr_type": "ITR-6",
                    "net_profit": 8.92067,  # lakhs
                    "current_ratio": 7.00,
                    "total_outside_liabilities": 393.73634,  # lakhs
                    "total_net_worth": 0.0
                },
                {
                    "financial_year": "2021-2022",
                    "assessment_year": "2022-2023",
                    "itr_type": "ITR-6",
                    "net_profit": 20.83685,  # lakhs
                    "current_ratio": 3.60,
                    "total_outside_liabilities": 190.93124,  # lakhs
                    "total_net_worth": 0.0
                }
            ]
        },

        "gst_sales_data": {
            "ttm_summary": {
                "period": "Aug'23 to Jul'24",
                "total_sales": 2411.48440,  # lakhs
                "b2b_customers": 930,
                "b2b_share_pct": 95.64,
                "top_5_customer_concentration_pct": 69.50,
                "top_5_geographic_concentration_pct": 96.02,
                "export_sales_pct": 4.19
            },
            "quarterly_breakdown": [
                {
                    "quarter": "Q1",
                    "year": "2024-25",
                    "external_invoice_count": 952,
                    "external_invoice_value": 921.49,
                    "external_taxable_value": 773.08,
                    "external_tax_payable": 148.23,
                    "gstr3b_sales": 762.13
                },
                {
                    "quarter": "Q2",
                    "year": "2024-25",
                    "external_invoice_count": 339,
                    "external_invoice_value": 323.71,
                    "external_taxable_value": 267.45,
                    "external_tax_payable": 56.22,
                    "gstr3b_sales": 267.45
                }
            ],
            "monthly_data": [
                {"month": "Jul'24", "gstr1": 267.45, "gstr2b": 241.41, "gstr3b": 267.45},
                {"month": "Jun'24", "gstr1": 342.17, "gstr2b": 366.08, "gstr3b": 342.17},
                {"month": "May'24", "gstr1": 252.8, "gstr2b": 288.47, "gstr3b": 252.8},
                {"month": "Apr'24", "gstr1": 178.11, "gstr2b": 207.34, "gstr3b": 178.11}
            ]
        },

        "gst_purchase_data": {
            "ttm_summary": {
                "period": "Aug'23 to Jul'24",
                "total_purchase": 589.93773,  # lakhs
                "suppliers": 293,
                "b2b_share_pct": 100.0,
                "top_5_supplier_concentration_pct": 59.82,
                "top_5_geographic_concentration_pct": 59.82
            },
            "quarterly_breakdown": [
                {
                    "quarter": "Q1",
                    "year": "2024-25",
                    "external_invoice_count": 459,
                    "external_invoice_value": 632.25,
                    "external_taxable_value": 525.93,
                    "itc_claimed": 105.03
                }
            ]
        },

        "sales_to_banking_credit": [
            {
                "month": "Sep-2024",
                "anchor": "HDFC",
                "gst_r1_value_with_tax": 20.65,
                "gst_r1_value_without_tax": 17.50,
                "gst_credit_debit": 0.00,
                "gst_nett": 20.65,
                "return_pct": 0.00,
                "bank_credit": 20.65,
                "bto_pct": 100.00
            }
        ],

        "books_of_accounts": [
            {
                "invoice_num": "101",
                "invoice_date": "01/12/2024",
                "party": "HDFC",
                "inv_amt_gst": 1.05,
                "inv_amt_without_gst": 1.00,
                "return_pct": 0,
                "new_value_invoice": 1.05,
                "tenure": 80,
                "due_date": "19/02/2025",
                "settled_money": 1.05,
                "collection_full": "Y",
                "collection_date": "05/03/2025",
                "real_tenure": 94,
                "bank_credit_verified": "Y"
            }
        ],

        "bank_limit_eligibility": {
            "total_12_month_sales": 2411.48,  # lakhs
            "current_wc_limits": 0.0,
            "wc_requirement_pct": 20.0,
            "total_current_serviceable_debt": 134.0,  # lakhs (from bureau)
            "acceptable_ratio_serviceable_debt_to_turnover": 25.0,
            "current_ratio_serviceable_debt_to_turnover": 0.0,
            "additional_wc_limits_sanctionable": 482.2968,  # lakhs
            "additional_annual_serviceable_capability": 602.8698,  # lakhs
            "additional_business_loan_3y_eligibility": 1512.5754  # lakhs (12% of annual serviceable capability)
        },

        "compliance_metrics": {
            "counter_party_compliance": {
                "as_on_aug_23": 0.29,
                "trailing_quarter_aug_23": 0.40
            },
            "sales_gstr1_counter_party_segment_stability": {
                "as_on_aug_23": 0.84,
                "trailing_quarter_aug_23": 0.84
            },
            "purchase_gstr2a_counter_party_segment_stability": {
                "as_on_aug_23": 0.84,
                "trailing_quarter_aug_23": 0.84
            }
        }
    }


def generate_mock_pan_verification(pan: str) -> Dict[str, Any]:
    """Generate mock PAN verification response"""
    return {
        "pan": pan,
        "name": "FINAGG TECHNOLOGIES PRIVATE LIMITED",
        "status": "active",
        "category": "company",
        "verification_date": datetime.now().isoformat()
    }


def generate_mock_gst_verification(gstin: str) -> Dict[str, Any]:
    """Generate mock GST verification response"""
    return {
        "gstin": gstin,
        "legal_name": "FINAGG TECHNOLOGIES PRIVATE LIMITED",
        "trade_name": "FINAGG TECHNOLOGIES PRIVATE LIMITED",
        "status": "active",
        "registration_date": "2021-02-21",
        "state_jurisdiction": gstin[:2],
        "taxpayer_type": "Regular",
        "constitution_of_business": "Private Limited Company",
        "verification_date": datetime.now().isoformat()
    }
