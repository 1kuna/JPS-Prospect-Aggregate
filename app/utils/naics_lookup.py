"""
NAICS Code to Description Lookup Utility
Provides standardized NAICS descriptions based on official NAICS 2022 codes
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# NAICS 2022 Official Descriptions - Common government procurement categories
NAICS_DESCRIPTIONS = {
    # Information Technology Services
    "541511": "Custom Computer Programming Services",
    "541512": "Computer Systems Design Services", 
    "541513": "Computer Facilities Management Services",
    "541519": "Other Computer Related Services",
    "541990": "All Other Professional, Scientific, and Technical Services",
    
    # Construction
    "236220": "Commercial and Institutional Building Construction",
    "237110": "Water and Sewer Line and Related Structures Construction",
    "237120": "Oil and Gas Pipeline and Related Structures Construction",
    "237130": "Power and Communication Line and Related Structures Construction",
    "237310": "Highway, Street, and Bridge Construction",
    "237990": "Other Heavy and Civil Engineering Construction",
    
    # Professional Services
    "541110": "Offices of Lawyers",
    "541211": "Offices of Certified Public Accountants",
    "541330": "Engineering Services",
    "541350": "Building Inspection Services",
    "541380": "Testing Laboratories",
    "541611": "Administrative Management and General Management Consulting Services",
    "541612": "Human Resources Consulting Services",
    "541613": "Marketing Consulting Services",
    "541618": "Other Management Consulting Services",
    "541690": "Other Scientific and Technical Consulting Services",
    "541715": "Research and Development in the Physical, Engineering, and Life Sciences",
    "541720": "Research and Development in the Social Sciences and Humanities",
    "541810": "Advertising Agencies",
    "541820": "Public Relations Agencies",
    "541830": "Media Buying Agencies",
    "541840": "Media Representatives",
    "541850": "Outdoor Advertising",
    "541860": "Direct Mail Advertising",
    "541870": "Advertising Material Distribution Services",
    "541890": "Other Services Related to Advertising",
    
    # Manufacturing - Defense/Government Common
    "334111": "Electronic Computer Manufacturing",
    "334112": "Computer Storage Device Manufacturing",
    "334118": "Computer Terminal and Other Computer Peripheral Equipment Manufacturing",
    "334220": "Radio and Television Broadcasting and Wireless Communications Equipment Manufacturing",
    "334290": "Other Communications Equipment Manufacturing",
    "334411": "Electron Tube Manufacturing",
    "334412": "Bare Printed Circuit Board Manufacturing",
    "334413": "Semiconductor and Related Device Manufacturing",
    "334414": "Electronic Capacitor Manufacturing",
    "334415": "Electronic Resistor Manufacturing",
    "334416": "Electronic Coil, Transformer, and Other Inductor Manufacturing",
    "334417": "Electronic Connector Manufacturing",
    "334418": "Printed Circuit Assembly (Electronic Assembly) Manufacturing",
    "334419": "Other Electronic Component Manufacturing",
    "334511": "Search, Detection, Navigation, Guidance, Aeronautical, and Nautical System and Instrument Manufacturing",
    "334512": "Automatic Environmental Control Manufacturing for Residential, Commercial, and Appliance Use",
    "334513": "Instruments and Related Products Manufacturing for Measuring, Displaying, and Controlling Industrial Process Variables",
    "334514": "Totalizing Fluid Meter and Counting Device Manufacturing",
    "334515": "Instrument Manufacturing for Measuring and Testing Electricity and Electrical Signals",
    "334516": "Analytical Laboratory Instrument Manufacturing",
    "334517": "Irradiation Apparatus Manufacturing",
    "334518": "Watch, Clock, and Part Manufacturing",
    "334519": "Other Measuring and Controlling Device Manufacturing",
    
    # Healthcare Services
    "621111": "Offices of Physicians (except Mental Health Specialists)",
    "621112": "Offices of Physicians, Mental Health Specialists",
    "621210": "Offices of Dentists",
    "621310": "Offices of Chiropractors",
    "621320": "Offices of Optometrists",
    "621330": "Offices of Mental Health Practitioners (except Physicians)",
    "621340": "Offices of Physical, Occupational and Speech Therapists, and Audiologists",
    "621391": "Offices of Podiatrists",
    "621399": "Offices of All Other Miscellaneous Health Practitioners",
    "621410": "Family Planning Centers",
    "621420": "Outpatient Mental Health and Substance Abuse Centers",
    "621491": "HMO Medical Centers",
    "621492": "Kidney Dialysis Centers",
    "621493": "Freestanding Ambulatory Surgical and Emergency Centers",
    "621498": "All Other Outpatient Care Centers",
    "621511": "Medical Laboratories",
    "621512": "Diagnostic Imaging Centers",
    "621610": "Home Health Care Services",
    "621910": "Ambulance Services",
    "621991": "Blood and Organ Banks",
    "621999": "All Other Miscellaneous Ambulatory Health Care Services",
    
    # Administrative and Support Services
    "561110": "Office Administrative Services",
    "561210": "Facilities Support Services",
    "561311": "Employment Placement Agencies",
    "561320": "Temporary Help Services",
    "561330": "Professional Employer Organizations",
    "561410": "Document Preparation Services",
    "561421": "Telephone Answering Services",
    "561422": "Telemarketing Bureaus and Other Contact Centers",
    "561431": "Private Mail Centers",
    "561439": "Other Business Service Centers (including Copy Shops)",
    "561440": "Collection Agencies",
    "561450": "Credit Bureaus",
    "561490": "Other Business Support Services",
    "561499": "All Other Business Support Services",
    "561510": "Travel Agencies",
    "561520": "Tour Operators",
    "561591": "Convention and Visitors Bureaus",
    "561599": "All Other Travel Arrangement and Reservation Services",
    "561611": "Investigation Services",
    "561612": "Security Guards and Patrol Services",
    "561613": "Armored Car Services",
    "561621": "Security Systems Services (except Locksmiths)",
    "561622": "Locksmiths",
    "561710": "Exterminating and Pest Control Services",
    "561720": "Janitorial Services",
    "561730": "Landscaping Services",
    "561740": "Carpet and Upholstery Cleaning Services",
    "561790": "Other Services to Buildings and Dwellings",
    "561910": "Packaging and Labeling Services",
    "561920": "Convention and Trade Show Organizers",
    "561990": "All Other Support Services",
    
    # Transportation and Warehousing
    "484110": "General Freight Trucking, Local",
    "484121": "General Freight Trucking, Long-Distance, Truckload",
    "484122": "General Freight Trucking, Long-Distance, Less Than Truckload",
    "488119": "Other Airport Operations",
    "488190": "Other Support Activities for Air Transportation",
    "488210": "Support Activities for Rail Transportation",
    "488310": "Port and Harbor Operations",
    "488320": "Marine Cargo Handling",
    "488330": "Navigational Services to Shipping",
    "488390": "Other Support Activities for Water Transportation",
    "488410": "Motor Vehicle Towing",
    "488490": "Other Support Activities for Road Transportation",
    "488510": "Freight Transportation Arrangement",
    "488991": "Packing and Crating",
    "488999": "All Other Support Activities for Transportation",
    "493110": "General Warehousing and Storage",
    "493120": "Refrigerated Warehousing and Storage",
    "493130": "Farm Product Warehousing and Storage",
    "493190": "Other Warehousing and Storage",
    
    # Education Services
    "611110": "Elementary and Secondary Schools",
    "611210": "Junior Colleges",
    "611310": "Colleges, Universities, and Professional Schools",
    "611420": "Computer Training",
    "611430": "Professional and Management Development Training",
    "611511": "Cosmetology and Barber Schools",
    "611512": "Flight Training",
    "611513": "Apprenticeship Training",
    "611519": "Other Technical and Trade Schools",
    "611610": "Fine Arts Schools",
    "611620": "Sports and Recreation Instruction",
    "611630": "Language Schools",
    "611691": "Exam Preparation and Tutoring",
    "611692": "Automobile Driving Schools",
    "611699": "All Other Miscellaneous Schools and Instruction",
    "611710": "Educational Support Services",
}

def get_naics_description(naics_code: str) -> Optional[str]:
    """
    Get the official NAICS description for a given 6-digit NAICS code.
    
    Args:
        naics_code: 6-digit NAICS code (e.g., "541511")
        
    Returns:
        Official NAICS description or None if code not found
    """
    if not naics_code:
        return None
        
    # Clean the code - remove any non-digits
    clean_code = ''.join(c for c in str(naics_code) if c.isdigit())
    
    # Validate 6-digit format
    if len(clean_code) != 6:
        logger.warning(f"Invalid NAICS code format: {naics_code}")
        return None
    
    return NAICS_DESCRIPTIONS.get(clean_code)

def validate_naics_code(naics_code: str) -> bool:
    """
    Validate if a NAICS code is properly formatted and exists in our lookup.
    
    Args:
        naics_code: NAICS code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not naics_code:
        return False
        
    # Clean the code
    clean_code = ''.join(c for c in str(naics_code) if c.isdigit())
    
    # Check format and existence
    return len(clean_code) == 6 and clean_code in NAICS_DESCRIPTIONS

def get_naics_info(naics_code: str) -> Dict[str, Optional[str]]:
    """
    Get comprehensive NAICS information for a code.
    
    Args:
        naics_code: 6-digit NAICS code
        
    Returns:
        Dict with 'code', 'description', and 'valid' keys
    """
    clean_code = ''.join(c for c in str(naics_code) if c.isdigit()) if naics_code else ""
    
    if len(clean_code) != 6:
        return {
            'code': naics_code,
            'description': None,
            'valid': False
        }
    
    description = NAICS_DESCRIPTIONS.get(clean_code)
    
    return {
        'code': clean_code,
        'description': description,
        'valid': description is not None
    }