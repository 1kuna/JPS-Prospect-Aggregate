"""
Optimized prompts for LLM enhancement operations
"""

NAICS_CLASSIFICATION_PROMPT = """You are a NAICS classification expert. Analyze ALL available procurement information to determine the TOP 3 most appropriate NAICS codes.

PROCUREMENT INFORMATION:
Title: "{title}"
Description: "{description}"
Agency: "{agency}"
Contract Type: "{contract_type}"
Set Aside: "{set_aside}"
Estimated Value: "{estimated_value}"
Additional Details: "{additional_info}"

Classification Guidelines:
1. Use NAICS 2022 edition codes (6-digit) - RETURN CODES ONLY, NO DESCRIPTIONS
2. Analyze ALL provided information - title, description, agency, contract type, etc.
3. Consider agency context (DOD=defense, HHS=healthcare, etc.)
4. Common government categories:
   - IT Services: 541511, 541512, 541513, 541519
   - Construction: 236220, 237110, 237310, 237990
   - Professional Services: 541330, 541611, 541618, 541690, 541715
   - Manufacturing: 334111, 334220, 334511, 334516
   - Healthcare: 621111, 621511, 621610
   - Administrative: 561110, 561210, 561320, 561612
5. Set-aside programs may indicate specific industry focus
6. Contract value can indicate complexity/scope
7. Be specific - use 6-digit codes, not 2-4 digit categories

IMPORTANT: Return ONLY codes - descriptions will be looked up separately from official NAICS database.

Return ONLY valid JSON array with up to 3 codes:
[
  {{"code": "541511", "confidence": 0.85}},
  {{"code": "541512", "confidence": 0.70}},
  {{"code": "541519", "confidence": 0.60}}
]

Confidence scoring:
- 0.9-1.0: Clear industry match with specific keywords/context
- 0.7-0.89: Good match but some ambiguity
- 0.5-0.69: Possible match, secondary service
- <0.5: Weak match but potentially relevant"""

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

def get_naics_prompt(title: str, description: str, agency: str = None, 
                     contract_type: str = None, set_aside: str = None, 
                     estimated_value: str = None, additional_info: str = None) -> str:
    """Get optimized NAICS classification prompt with all available information"""
    prompt = NAICS_CLASSIFICATION_PROMPT
    prompt = prompt.replace("{title}", title or "Not provided")
    prompt = prompt.replace("{description}", description or "Not provided")
    prompt = prompt.replace("{agency}", agency or "Not provided")
    prompt = prompt.replace("{contract_type}", contract_type or "Not provided")
    prompt = prompt.replace("{set_aside}", set_aside or "Not provided")
    prompt = prompt.replace("{estimated_value}", estimated_value or "Not provided")
    prompt = prompt.replace("{additional_info}", additional_info or "Not provided")
    return prompt

def get_value_prompt(value_text: str) -> str:
    """Get optimized value parsing prompt"""
    prompt = VALUE_PARSING_PROMPT
    prompt = prompt.replace("{value_text}", value_text or "")
    return prompt

def get_contact_prompt(contact_data: str) -> str:
    """Get optimized contact extraction prompt"""
    import json
    if isinstance(contact_data, dict):
        contact_data = json.dumps(contact_data, indent=2)
    prompt = CONTACT_EXTRACTION_PROMPT
    prompt = prompt.replace("{contact_data}", contact_data or "")
    return prompt

def get_title_prompt(title: str, description: str, agency: str) -> str:
    """Get optimized title enhancement prompt"""
    prompt = TITLE_ENHANCEMENT_PROMPT
    prompt = prompt.replace("{title}", title or "No title provided")
    prompt = prompt.replace("{description}", description or "No description available")
    prompt = prompt.replace("{agency}", agency or "Unknown agency")
    return prompt