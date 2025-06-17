"""
Optimized prompts for LLM enhancement operations
"""

NAICS_CLASSIFICATION_PROMPT = """You are a NAICS classification expert. Analyze the contract title and description to determine the most appropriate NAICS code.

Title: "{title}"
Description: "{description}"

Important Guidelines:
1. Use NAICS 2022 edition codes (6-digit)
2. Focus on the PRIMARY service/product being procured
3. Common government categories:
   - IT Services: 541511, 541512, 541513, 541519
   - Construction: 236xxx, 237xxx
   - Professional Services: 541xxx
   - Manufacturing: 31xxxx-33xxxx
   - Healthcare: 621xxx, 622xxx
4. Consider the procuring agency context
5. Be specific - use 6-digit codes, not 2-4 digit categories

Return ONLY valid JSON:
{{"code": "541511", "description": "Custom Computer Programming Services", "confidence": 0.85}}

Your confidence should reflect:
- 0.9-1.0: Clear industry match with specific keywords
- 0.7-0.89: Good match but some ambiguity
- 0.5-0.69: Multiple possible industries
- <0.5: Insufficient information"""

VALUE_PARSING_PROMPT = """You are a contract value parser. Extract and normalize the monetary value from the given text.

Value Text: "{value_text}"

Parsing Rules:
1. Common patterns to recognize:
   - Ranges: "$1M-$5M", ">$250K to <$750K", "between $X and $Y", "$250,000 to $700,000"
   - Single values: "$2.5 million", "NTE $500K", "up to $10M"
   - Abbreviations: K=thousand, M/MM=million, B=billion
   - Multi-year: "5-year $10M" = $10M total (not $50M)
   
2. For ranges:
   - min: lower bound
   - max: upper bound  
   - single: midpoint or best estimate
   - IMPORTANT: ">$250K to <$750K" means min=250000, max=750000
   - IMPORTANT: "$250,000 to $700,000" means min=250000, max=700000
   
3. For single values:
   - Use the same value for min, max, and single
   
4. Special cases:
   - "Greater than X": min=X, max=X*2, single=X*1.5
   - "Less than X": min=X*0.5, max=X, single=X*0.75
   - "Up to X" or "NTE X": min=X*0.5, max=X, single=X*0.75
   - IMPORTANT: Parse each number in a range separately - don't repeat the first number

Return ONLY valid JSON (numbers only, no formatting):
{{"min": 1000000, "max": 5000000, "single": 3000000}}"""

CONTACT_EXTRACTION_PROMPT = """You are a government contact information extractor. Identify the PRIMARY point of contact for this procurement.

Contact Data:
{contact_data}

Selection Priorities:
1. Program/Technical POCs > Administrative contacts
2. Contracting Officers > General contacts
3. People with procurement-specific titles
4. Most complete contact info (both name and email)

Common government email patterns:
- firstname.lastname@agency.gov
- firstname.m.lastname@agency.mil
- firstname.lastname.civ@mail.mil

Titles indicating primary contacts:
- Contracting Officer (CO)
- Contract Specialist (CS)
- Program Manager (PM)
- Technical POC
- Requirements POC

Return ONLY valid JSON:
{{"email": "john.smith@agency.gov", "name": "John Smith", "confidence": 0.9}}

Confidence guidelines:
- 0.9-1.0: Clear primary contact with full info
- 0.7-0.89: Likely primary contact, may be missing some info
- 0.5-0.69: Multiple contacts, unclear which is primary
- <0.5: No clear contact information"""

TITLE_ENHANCEMENT_PROMPT = """You are a government procurement title optimizer. Your job is to rewrite vague, unclear, or generic procurement titles into clear, descriptive, actionable titles that accurately reflect what is being procured.

Original Title: "{title}"
Description: "{description}"
Agency: "{agency}"

Guidelines for enhanced titles:
1. BE SPECIFIC: Replace vague terms with specific ones
   - Bad: "Services" → Good: "IT Support Services"
   - Bad: "Support" → Good: "Maintenance and Technical Support"
   - Bad: "Requirements" → Good: "Software Development Requirements"

2. INCLUDE KEY DETAILS: Add important context from description
   - Include technology/system names if mentioned
   - Include location if relevant
   - Include duration if it's a key characteristic

3. MAKE IT ACTIONABLE: Use action-oriented language
   - "Development of..." "Procurement of..." "Maintenance of..."
   - Avoid passive constructions

4. KEEP GOVERNMENT CONTEXT: Preserve important government/military terminology
   - Keep acronyms that are widely understood
   - Preserve security classifications if mentioned
   - Keep agency-specific terms that add value

5. OPTIMAL LENGTH: 8-15 words typically
   - Long enough to be descriptive
   - Short enough to be scannable
   - Remove unnecessary articles (a, an, the) if it improves flow

6. EXAMPLES:
   - "IT Services" → "Cloud Infrastructure Development and Migration Services"
   - "Support Services" → "Help Desk and User Support Services for DOD Systems"
   - "Requirements Document" → "Technical Requirements for Enterprise Software Modernization"
   - "Professional Services" → "Cybersecurity Assessment and Implementation Services"

Return ONLY valid JSON:
{{"enhanced_title": "Clear Descriptive Title Here", "confidence": 0.85, "reasoning": "Brief explanation of changes made"}}

Confidence guidelines:
- 0.9-1.0: Original title was very vague, significant improvement made
- 0.7-0.89: Moderate improvement, some ambiguity resolved
- 0.5-0.69: Minor improvement, original was somewhat clear
- <0.5: Original title was already clear, minimal changes needed"""

def get_naics_prompt(title: str, description: str) -> str:
    """Get optimized NAICS classification prompt"""
    return NAICS_CLASSIFICATION_PROMPT.format(title=title, description=description)

def get_value_prompt(value_text: str) -> str:
    """Get optimized value parsing prompt"""
    return VALUE_PARSING_PROMPT.format(value_text=value_text)

def get_contact_prompt(contact_data: str) -> str:
    """Get optimized contact extraction prompt"""
    import json
    if isinstance(contact_data, dict):
        contact_data = json.dumps(contact_data, indent=2)
    return CONTACT_EXTRACTION_PROMPT.format(contact_data=contact_data)

def get_title_prompt(title: str, description: str, agency: str) -> str:
    """Get optimized title enhancement prompt"""
    return TITLE_ENHANCEMENT_PROMPT.format(
        title=title or "No title provided",
        description=description or "No description available", 
        agency=agency or "Unknown agency"
    )