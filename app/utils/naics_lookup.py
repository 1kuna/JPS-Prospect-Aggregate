"""
NAICS Code to Description Lookup Utility
Provides standardized NAICS descriptions based on official NAICS 2022 codes
"""

from typing import Optional, Dict
from app.utils.logger import logger

# NAICS 2022 Complete Lookup Table
# Generated from official NAICS data - 498 total 6-digit codes
NAICS_DESCRIPTIONS = {
    # Agriculture, Forestry, Fishing and Hunting
    "111110": "Soybean Farming",
    "111120": "Oilseed (except Soybean) Farming",
    "111130": "Dry Pea and Bean Farming",
    "111140": "Wheat Farming",
    "111150": "Corn Farming",
    "111160": "Rice Farming",
    "111211": "Potato Farming",
    "111219": "Other Vegetable (except Potato) and Melon Farming",
    "111310": "Orange Groves",
    "111320": "Citrus (except Orange) Groves",
    "111411": "Mushroom Production",
    "111419": "Other Food Crops Grown Under Cover",
    "111421": "Nursery and Tree Production",
    "111422": "Floriculture Production",
    "111910": "Tobacco Farming",
    "111920": "Cotton Farming",
    "111930": "Sugar Cane Farming",
    "111940": "Hay Farming",
    "112120": "Dairy Cattle and Milk Production",
    "112210": "Hog and Pig Farming",
    "112310": "Chicken Egg Production",
    "112320": "Broiler and Other Meat-Type Chicken Production",
    "112330": "Turkey Production",
    "112340": "Poultry Hatcheries",
    "112410": "Sheep Farming",
    "112420": "Goat Farming",
    "112910": "Apiculture",
    "112920": "Horse and Other Equine Production",
    "112930": "Fur-Bearing Animal and Rabbit Production",
    "113110": "Timber Tract Operations",
    "113210": "Forest Nurseries and Gathering of Forest Products",
    "114210": "Hunting and Trapping",
    "115210": "Support Activities for Animal Production",
    "115310": "Support Activities for Forestry",
    # Mining, Quarrying, and Oil and Gas Extraction
    "212210": "Iron Ore Mining",
    "212231": "Lead-Zinc Ore Mining",
    "212291": "Uranium Ore Mining",
    "212299": "All Other Metal Ore Mining",
    "213111": "Oil and Gas Contract Drilling",
    # Utilities
    "221111": "Hydro-Electric Power Generation",
    "221112": "Fossil-Fuel Electric Power Generation",
    "221113": "Nuclear Electric Power Generation",
    "221119": "Other Electric Power Generation",
    "221121": "Electric Bulk Power Transmission and Control",
    "221122": "Electric Power Distribution",
    "221210": "Natural Gas Distribution",
    "221310": "Water Supply and Irrigation Systems",
    "221320": "Sewage Treatment Facilities",
    "221330": "Steam and Air-Conditioning Supply",
    # Construction
    "236210": "Industrial Building and Structure Construction",
    "236220": "Commercial and Institutional Building Construction",
    "237110": "Water and Sewer Line and Related Structures Construction",
    "237120": "Oil and Gas Pipeline and Related Structures Construction",
    "237130": "Power and Communication Line and Related Structures Construction",
    "237210": "Land Subdivision",
    "237310": "Highway, Street and Bridge Construction",
    "237990": "Other Heavy and Civil Engineering Construction",
    "238110": "Poured Concrete Foundation and Structure Contractors",
    "238120": "Structural Steel and Precast Concrete Contractors",
    "238130": "Framing Contractors",
    "238140": "Masonry Contractors",
    "238150": "Glass and Glazing Contractors",
    "238160": "Roofing Contractors",
    "238170": "Siding Contractors",
    "238190": "Other Foundation, Structure and Building Exterior Contractors",
    "238210": "Electrical Contractors and Other Wiring Installation Contractors",
    "238220": "Plumbing, Heating and Air-Conditioning Contractors",
    "238310": "Drywall and Insulation Contractors",
    "238320": "Painting and Wall Covering Contractors",
    "238330": "Flooring Contractors",
    "238340": "Tile and Terrazzo Contractors",
    "238350": "Finish Carpentry Contractors",
    "238390": "Other Building Finishing Contractors",
    "238910": "Site Preparation Contractors",
    "238990": "All Other Specialty Trade Contractors",
    # Manufacturing (Food, Textiles, etc.)
    "311111": "Dog and Cat Food Manufacturing",
    "311119": "Other Animal Food Manufacturing",
    "311211": "Flour Milling",
    "311221": "Wet Corn Milling",
    "311225": "Fat and Oil Refining and Blending",
    "311230": "Breakfast Cereal Manufacturing",
    "311320": "Chocolate and Confectionery Manufacturing from Cacao Beans",
    "311330": "Confectionery Manufacturing from Purchased Chocolate",
    "311340": "Non-Chocolate Confectionery Manufacturing",
    "311511": "Fluid Milk Manufacturing",
    "311520": "Ice Cream and Frozen Dessert Manufacturing",
    "311611": "Animal (except Poultry) Slaughtering",
    "311615": "Poultry Processing",
    "311811": "Retail Bakeries",
    "311821": "Cookie and Cracker Manufacturing",
    "311822": "Flour Mixes and Dough Manufacturing from Purchased Flour",
    "311823": "Dry Pasta Manufacturing",
    "311830": "Tortilla Manufacturing",
    "311911": "Roasted Nut and Peanut Butter Manufacturing",
    "311919": "Other Snack Food Manufacturing",
    "311920": "Coffee and Tea Manufacturing",
    "311930": "Flavouring Syrup and Concentrate Manufacturing",
    "312120": "Breweries",
    "312130": "Wineries",
    "312140": "Distilleries",
    "312210": "Tobacco Stemming and Redrying",
    "313210": "Broad-Woven Fabric Mills",
    "313230": "Nonwoven Fabric Mills",
    "313320": "Fabric Coating",
    "314110": "Carpet and Rug Mills",
    "315221": "Men's and Boys' Cut and Sew Underwear and Nightwear Manufacturing",
    "315222": "Men's and Boys' Cut and Sew Suit, Coat and Overcoat Manufacturing",
    "315231": "Women's and Girls' Cut and Sew Lingerie, Loungewear and Nightwear Manufacturing",
    "315232": "Women's and Girls' Cut and Sew Blouse and Shirt Manufacturing",
    "315233": "Women's and Girls' Cut and Sew Dress Manufacturing",
    "315234": "Women's and Girls' Cut and Sew Suit, Coat, Tailored Jacket and Skirt Manufacturing",
    "315239": "Other Women's and Girls' Cut and Sew Clothing Manufacturing",
    "315291": "Infants' Cut and Sew Clothing Manufacturing",
    "315292": "Fur and Leather Clothing Manufacturing",
    "315299": "All Other Cut and Sew Clothing Manufacturing",
    "316110": "Leather and Hide Tanning and Finishing",
    # Manufacturing (Wood, Paper, etc.)
    "321114": "Wood Preservation",
    "321211": "Hardwood Veneer and Plywood Mills",
    "321212": "Softwood Veneer and Plywood Mills",
    "321911": "Wood Window and Door Manufacturing",
    "321920": "Wood Container and Pallet Manufacturing",
    "321991": "Manufactured (Mobile) Home Manufacturing",
    "321992": "Prefabricated Wood Building Manufacturing",
    "321999": "All Other Miscellaneous Wood Product Manufacturing",
    "322121": "Paper (except Newsprint) Mills",
    "322122": "Newsprint Mills",
    "322130": "Paperboard Mills",
    "322211": "Corrugated and Solid Fibre Box Manufacturing",
    "322212": "Folding Paperboard Box Manufacturing",
    "322291": "Sanitary Paper Product Manufacturing",
    "322299": "All Other Converted Paper Product Manufacturing",
    "323113": "Commercial Screen Printing",
    "323114": "Quick Printing",
    "323115": "Digital Printing",
    "323116": "Manifold Business Forms Printing",
    "324110": "Petroleum Refineries",
    "324121": "Asphalt Paving Mixture and Block Manufacturing",
    "324122": "Asphalt Shingle and Coating Material Manufacturing",
    "325110": "Petrochemical Manufacturing",
    "325120": "Industrial Gas Manufacturing",
    "325181": "Alkali and Chlorine Manufacturing",
    "325314": "Mixed Fertilizer Manufacturing",
    "325320": "Pesticide and Other Agricultural Chemical Manufacturing",
    "325510": "Paint and Coating Manufacturing",
    "325520": "Adhesive Manufacturing",
    "325620": "Toilet Preparation Manufacturing",
    "325910": "Printing Ink Manufacturing",
    "325920": "Explosives Manufacturing",
    "325991": "Custom Compounding of Purchased Resins",
    "326111": "Plastic Bag and Pouch Manufacturing",
    "326121": "Unlaminated Plastic Profile Shape Manufacturing",
    "326122": "Plastic Pipe and Pipe Fitting Manufacturing",
    "326130": "Laminated Plastic Plate, Sheet (except Packaging), and Shape Manufacturing",
    "326140": "Polystyrene Foam Product Manufacturing",
    "326150": "Urethane and Other Foam Product (except Polystyrene) Manufacturing",
    "326160": "Plastic Bottle Manufacturing",
    "326191": "Plastic Plumbing Fixture Manufacturing",
    "326220": "Rubber and Plastic Hose and Belting Manufacturing",
    "327215": "Glass Product Manufacturing from Purchased Glass",
    "327310": "Cement Manufacturing",
    "327320": "Ready-Mix Concrete Manufacturing",
    "327390": "Other Concrete Product Manufacturing",
    "327410": "Lime Manufacturing",
    "327420": "Gypsum Product Manufacturing",
    "327910": "Abrasive Product Manufacturing",
    # Manufacturing (Chemicals, Metals, etc.)
    "331210": "Iron and Steel Pipes and Tubes Manufacturing from Purchased Steel",
    "331221": "Cold-Rolled Steel Shape Manufacturing",
    "331222": "Steel Wire Drawing",
    "331511": "Iron Foundries",
    "332311": "Prefabricated Metal Building and Component Manufacturing",
    "332321": "Metal Window and Door Manufacturing",
    "332410": "Power Boiler and Heat Exchanger Manufacturing",
    "332420": "Metal Tank (Heavy Gauge) Manufacturing",
    "332431": "Metal Can Manufacturing",
    "332439": "Other Metal Container Manufacturing",
    "332510": "Hardware Manufacturing",
    "332611": "Spring (Heavy Gauge) Manufacturing",
    "332710": "Machine Shops",
    "332991": "Ball and Roller Bearing Manufacturing",
    "333120": "Construction Machinery Manufacturing",
    "333210": "Sawmill and Woodworking Machinery Manufacturing",
    "333220": "Rubber and Plastics Industry Machinery Manufacturing",
    "333291": "Paper Industry Machinery Manufacturing",
    "333511": "Industrial Mould Manufacturing",
    "333611": "Turbine and Turbine Generator Set Unit Manufacturing",
    "334111": "Electronic Computer Manufacturing",
    "334112": "Computer Storage Device Manufacturing",
    "334118": "Computer Terminal and Other Computer Peripheral Equipment Manufacturing",
    "334210": "Telephone Apparatus Manufacturing",
    "334220": "Radio and Television Broadcasting and Wireless Communications Equipment Manufacturing",
    "334290": "Other Communications Equipment Manufacturing",
    "334310": "Audio and Video Equipment Manufacturing",
    "334411": "Electron Tube Manufacturing",
    "334412": "Bare Printed Circuit Board Manufacturing",
    "334413": "Semiconductor and Related Device Manufacturing",
    "334414": "Electronic Capacitor Manufacturing",
    "334415": "Electronic Resistor Manufacturing",
    "334416": "Electronic Coil, Transformer, and Other Inductor Manufacturing",
    "334417": "Electronic Connector Manufacturing",
    "334418": "Printed Circuit Assembly (Electronic Assembly) Manufacturing",
    "334419": "Other Electronic Component Manufacturing",
    "334511": "Navigational and Guidance Instruments Manufacturing",
    "334512": "Automatic Environmental Control Manufacturing for Residential, Commercial, and Appliance Use",
    "334513": "Instruments and Related Products Manufacturing for Measuring, Displaying, and Controlling Industrial Process Variables",
    "334514": "Totalizing Fluid Meter and Counting Device Manufacturing",
    "334515": "Instrument Manufacturing for Measuring and Testing Electricity and Electrical Signals",
    "334516": "Analytical Laboratory Instrument Manufacturing",
    "334517": "Irradiation Apparatus Manufacturing",
    "334518": "Watch, Clock, and Part Manufacturing",
    "334519": "Other Measuring and Controlling Device Manufacturing",
    "335110": "Electric Lamp Bulb and Parts Manufacturing",
    "335311": "Power, Distribution and Specialty Transformers Manufacturing",
    "335312": "Motor and Generator Manufacturing",
    "336120": "Heavy-Duty Truck Manufacturing",
    "336211": "Motor Vehicle Body Manufacturing",
    "336212": "Truck Trailer Manufacturing",
    "336330": "Motor Vehicle Steering and Suspension Components (except Spring) Manufacturing",
    "336340": "Motor Vehicle Brake System Manufacturing",
    "336350": "Motor Vehicle Transmission and Power Train Parts Manufacturing",
    "336360": "Motor Vehicle Seating and Interior Trim Manufacturing",
    "336370": "Motor Vehicle Metal Stamping",
    "336510": "Railroad Rolling Stock Manufacturing",
    "336611": "Ship Building and Repairing",
    "336612": "Boat Building",
    "337110": "Wood Kitchen Cabinet and Counter Top Manufacturing",
    "337121": "Upholstered Household Furniture Manufacturing",
    "337127": "Institutional Furniture Manufacturing",
    "337214": "Office Furniture (except Wood) Manufacturing",
    "337215": "Showcase, Partition, Shelving and Locker Manufacturing",
    "337910": "Mattress Manufacturing",
    "337920": "Blind and Shade Manufacturing",
    # Wholesale Trade
    "419110": "Business-to-Business Electronic Markets",
    "419120": "Wholesale Trade Agents and Brokers",
    # Retail Trade (Motor Vehicles, etc.)
    "441110": "New Car Dealers",
    "441120": "Used Car Dealers",
    "441210": "Recreational Vehicle Dealers",
    "441310": "Automotive Parts and Accessories Stores",
    "441320": "Tire Dealers",
    "442110": "Furniture Stores",
    "442210": "Floor Covering Stores",
    "442291": "Window Treatment Stores",
    "443120": "Computer and Software Stores",
    "443130": "Camera and Photographic Supplies Stores",
    "444110": "Home Centres",
    "444120": "Paint and Wallpaper Stores",
    "444130": "Hardware Stores",
    "444190": "Other Building Material Dealers",
    "444210": "Outdoor Power Equipment Stores",
    "444220": "Nursery Stores and Garden Centres",
    "445110": "Supermarkets and Other Grocery (except Convenience) Stores",
    "445120": "Convenience Stores",
    "445210": "Meat Markets",
    "445220": "Fish and Seafood Markets",
    "445230": "Fruit and Vegetable Markets",
    "445291": "Baked Goods Stores",
    "445292": "Confectionery and Nut Stores",
    "445299": "All Other Specialty Food Stores",
    "445310": "Beer, Wine and Liquor Stores",
    "446110": "Pharmacies and Drug Stores",
    "446120": "Cosmetics, Beauty Supplies and Perfume Stores",
    "446130": "Optical Goods Stores",
    "446191": "Food (Health) Supplement Stores",
    "446199": "All Other Health and Personal Care Stores",
    "447110": "Gasoline Stations with Convenience Stores",
    "447190": "Other Gasoline Stations",
    "448110": "Men's Clothing Stores",
    "448120": "Women's Clothing Stores",
    "448130": "Children's and Infants' Clothing Stores",
    "448140": "Family Clothing Stores",
    "448150": "Clothing Accessories Stores",
    "448210": "Shoe Stores",
    "448310": "Jewellery Stores",
    "448320": "Luggage and Leather Goods Stores",
    # Retail Trade (General Merchandise, etc.)
    "451110": "Sporting Goods Stores",
    "451120": "Hobby, Toy and Game Stores",
    "451130": "Sewing, Needlework and Piece Goods Stores",
    "451140": "Musical Instrument and Supplies Stores",
    "451220": "Pre-Recorded Tape, Compact Disc and Record Stores",
    "452910": "Warehouse Clubs and Superstores",
    "453110": "Florists",
    "453210": "Office Supplies and Stationery Stores",
    "453220": "Gift, Novelty and Souvenir Stores",
    "453310": "Used Merchandise Stores",
    "453910": "Pet and Pet Supplies Stores",
    "453920": "Art Dealers",
    "453930": "Mobile Home Dealers",
    "454111": "Internet Shopping",
    "454112": "Electronic Auctions",
    "454113": "Mail-Order Houses",
    "454210": "Vending Machine Operators",
    "454311": "Heating Oil Dealers",
    "454312": "Liquefied Petroleum Gas (Bottled Gas) Dealers",
    "454319": "Other Fuel Dealers",
    "454390": "Other Direct Selling Establishments",
    # Transportation and Warehousing
    "482112": "Short-Haul Freight Rail Transportation",
    "484110": "General Freight Trucking, Local",
    "484121": "General Freight Trucking, Long Distance, Truck-Load",
    "484122": "General Freight Trucking, Long Distance, Less Than Truck-Load",
    "484210": "Used Household and Office Goods Moving",
    "485210": "Interurban and Rural Bus Transportation",
    "485310": "Taxi Service",
    "485320": "Limousine Service",
    "485410": "School and Employee Bus Transportation",
    "485510": "Charter Bus Industry",
    "486110": "Pipeline Transportation of Crude Oil",
    "486210": "Pipeline Transportation of Natural Gas",
    "486910": "Pipeline Transportation of Refined Petroleum Products",
    "486990": "All Other Pipeline Transportation",
    "487110": "Scenic and Sightseeing Transportation, Land",
    "487210": "Scenic and Sightseeing Transportation, Water",
    "487990": "Scenic and Sightseeing Transportation, Other",
    "488111": "Air Traffic Control",
    "488119": "Other Airport Operations",
    "488190": "Other Support Activities for Air Transportation",
    "488210": "Support Activities for Rail Transportation",
    "488310": "Port and Harbour Operations",
    "488320": "Marine Cargo Handling",
    "488390": "Other Support Activities for Water Transportation",
    "488410": "Motor Vehicle Towing",
    "488490": "Other Support Activities for Road Transportation",
    "491110": "Postal Service",
    "492110": "Couriers",
    "492210": "Local Messengers and Local Delivery",
    "493110": "General Warehousing and Storage",
    "493120": "Refrigerated Warehousing and Storage",
    "493130": "Farm Product Warehousing and Storage",
    "493190": "Other Warehousing and Storage",
    # Information
    "511110": "Newspaper Publishers",
    "511120": "Periodical Publishers",
    "511130": "Book Publishers",
    "511140": "Directory and Mailing List Publishers",
    "511210": "Software Publishers",
    "512110": "Motion Picture and Video Production",
    "512120": "Motion Picture and Video Distribution",
    "512210": "Record Production",
    "512220": "Integrated Record Production/Distribution",
    "512230": "Music Publishers",
    "512240": "Sound Recording Studios",
    "512290": "Other Sound Recording Industries",
    "515120": "Television Broadcasting",
    "515210": "Pay and Specialty Television",
    "517410": "Satellite Telecommunications",
    "517910": "Other Telecommunications",
    "518210": "Data Processing, Hosting, and Related Services",
    "519110": "News Syndicates",
    "519130": "Internet Publishing and Broadcasting, and Web Search Portals",
    "519190": "All Other Information Services",
    # Finance and Insurance
    "521110": "Monetary Authorities - Central Bank",
    "522130": "Local Credit Unions",
    "522190": "Other Depository Credit Intermediation",
    "522210": "Credit Card Issuing",
    "522220": "Sales Financing",
    "522291": "Consumer Lending",
    "522310": "Mortgage and Non-mortgage Loan Brokers",
    "522390": "Other Activities Related to Credit Intermediation",
    "523110": "Investment Banking and Securities Dealing",
    "523120": "Securities Brokerage",
    "523130": "Commodity Contracts Dealing",
    "523140": "Commodity Contracts Brokerage",
    "523210": "Securities and Commodity Exchanges",
    "523910": "Miscellaneous Intermediation",
    "523920": "Portfolio Management",
    "523930": "Investment Advice",
    "524210": "Insurance Agencies and Brokerages",
    "524291": "Claims Adjusters",
    # Real Estate and Rental and Leasing
    "531120": "Lessors of Non-Residential Buildings (except Mini-Warehouses)",
    "531130": "Self-Storage Mini-Warehouses",
    "531190": "Lessors of Other Real Estate Property",
    "531320": "Offices of Real Estate Appraisers",
    "531390": "Other Activities Related to Real Estate",
    "532111": "Passenger Car Rental",
    "532112": "Passenger Car Leasing",
    "532120": "Truck, Utility Trailer and RV (Recreational Vehicle) Rental and Leasing",
    "532210": "Consumer Electronics and Appliance Rental",
    "532220": "Formal Wear and Costume Rental",
    "532230": "Video Tape and Disc Rental",
    "532310": "General Rental Centres",
    "532420": "Office Machinery and Equipment Rental and Leasing",
    "532490": "Other Commercial and Industrial Machinery and Equipment Rental and Leasing",
    "533110": "Lessors of Non-Financial Intangible Assets (Except Copyrighted Works)",
    # Professional, Scientific, and Technical Services
    "541110": "Offices of Lawyers",
    "541120": "Offices of Notaries",
    "541211": "Offices of Certified Public Accountants",
    "541213": "Tax Preparation Services",
    "541310": "Architectural Services",
    "541320": "Landscape Architectural Services",
    "541330": "Engineering Services",
    "541340": "Drafting Services",
    "541350": "Building Inspection Services",
    "541360": "Geophysical Surveying and Mapping Services",
    "541370": "Surveying and Mapping (except Geophysical) Services",
    "541380": "Testing Laboratories",
    "541410": "Interior Design Services",
    "541420": "Industrial Design Services",
    "541430": "Graphic Design Services",
    "541490": "Other Specialized Design Services",
    "541511": "Custom Computer Programming Services",
    "541512": "Computer Systems Design Services",
    "541513": "Computer Facilities Management Services",
    "541519": "Other Computer Related Services",
    "541611": "Administrative Management and General Management Consulting Services",
    "541612": "Human Resources Consulting Services",
    "541613": "Marketing Consulting Services",
    "541618": "Other Management Consulting Services",
    "541620": "Environmental Consulting Services",
    "541690": "Other Scientific and Technical Consulting Services",
    "541715": "Research and Development in the Physical, Engineering, and Life Sciences",
    "541720": "Research and Development in the Social Sciences and Humanities",
    "541810": "Advertising Agencies",
    "541820": "Public Relations Services",
    "541830": "Media Buying Agencies",
    "541840": "Media Representatives",
    "541850": "Display Advertising",
    "541860": "Direct Mail Advertising",
    "541870": "Advertising Material Distribution Services",
    "541890": "Other Services Related to Advertising",
    "541910": "Marketing Research and Public Opinion Polling",
    "541930": "Translation and Interpretation Services",
    "541940": "Veterinary Services",
    "541990": "All Other Professional, Scientific and Technical Services",
    # Management of Companies and Enterprises
    "551114": "Head Offices",
    # Administrative and Support and Waste Management Services
    "561110": "Office Administrative Services",
    "561210": "Facilities Support Services",
    "561310": "Employment Placement Agencies and Executive Search Services",
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
    "561612": "Security Guard and Patrol Services",
    "561613": "Armoured Car Services",
    "561621": "Security Systems Services (except Locksmiths)",
    "561622": "Locksmiths",
    "561710": "Exterminating and Pest Control Services",
    "561720": "Janitorial Services",
    "561730": "Landscaping Services",
    "561740": "Carpet and Upholstery Cleaning Services",
    "561790": "Other Services to Buildings and Dwellings",
    "561910": "Packaging and Labelling Services",
    "561920": "Convention and Trade Show Organizers",
    "561990": "All Other Support Services",
    "562910": "Remediation Services",
    "562920": "Material Recovery Facilities",
    # Educational Services
    "611110": "Elementary and Secondary Schools",
    "611210": "Community Colleges and C.E.G.E.P.s",
    "611310": "Universities",
    "611410": "Business and Secretarial Schools",
    "611420": "Computer Training",
    "611430": "Professional and Management Development Training",
    "611511": "Cosmetology and Barber Schools",
    "611512": "Flight Training",
    "611513": "Apprenticeship Training",
    "611519": "Other Technical and Trade Schools",
    "611610": "Fine Arts Schools",
    "611620": "Athletic Instruction",
    "611630": "Language Schools",
    "611691": "Exam Preparation and Tutoring",
    "611692": "Automobile Driving Schools",
    "611699": "All Other Miscellaneous Schools and Instruction",
    "611710": "Educational Support Services",
    # Health Care and Social Assistance
    "621111": "Offices of Physicians (except Mental Health Specialists)",
    "621112": "Offices of Physicians, Mental Health Specialists",
    "621210": "Offices of Dentists",
    "621310": "Offices of Chiropractors",
    "621320": "Offices of Optometrists",
    "621330": "Offices of Mental Health Practitioners (except Physicians)",
    "621340": "Offices of Physical, Occupational, and Speech Therapists and Audiologists",
    "621391": "Offices of Podiatrists",
    "621399": "Offices of All Other Miscellaneous Health Practitioners",
    "621410": "Family Planning Centres",
    "621420": "Out-Patient Mental Health and Substance Abuse Centres",
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
    "622210": "Psychiatric and Substance Abuse Hospitals",
    "622310": "Specialty (except Psychiatric and Substance Abuse) Hospitals",
    "623110": "Nursing Care Facilities",
    "623210": "Residential Developmental Handicap Facilities",
    "624110": "Child and Youth Services",
    "624120": "Services for the Elderly and Persons with Disabilities",
    "624190": "Other Individual and Family Services",
    "624210": "Community Food Services",
    "624230": "Emergency and Other Relief Services",
    "624310": "Vocational Rehabilitation Services",
    "624410": "Child Day-Care Services",
    # Arts, Entertainment, and Recreation
    "711120": "Dance Companies",
    "711130": "Musical Groups and Artists",
    "711190": "Other Performing Arts Companies",
    "711211": "Sports Teams and Clubs",
    "711410": "Agents and Managers for Artists, Athletes, Entertainers and Other Public Figures",
    "712120": "Historic and Heritage Sites",
    "712130": "Zoos and Botanical Gardens",
    "712190": "Nature Parks and Other Similar Institutions",
    "713110": "Amusement and Theme Parks",
    "713120": "Amusement Arcades",
    "713210": "Casinos (except Casino Hotels)",
    "713910": "Golf Courses and Country Clubs",
    "713920": "Skiing Facilities",
    "713930": "Marinas",
    "713940": "Fitness and Recreational Sports Centres",
    "713950": "Bowling Centres",
    "713990": "All Other Amusement and Recreation Industries",
    # Accommodation and Food Services
    "721120": "Casino Hotels",
    "721191": "Bed and Breakfast",
    "721211": "RV (Recreational Vehicle) Parks and Campgrounds",
    "721310": "Rooming and Boarding Houses",
    "722110": "Full-Service Restaurants",
    "722310": "Food Service Contractors",
    "722320": "Caterers",
    "722330": "Mobile Food Services",
    "722410": "Drinking Places (Alcoholic Beverages)",
    # Other Services (except Public Administration)
    "811111": "General Automotive Repair",
    "811112": "Automotive Exhaust System Repair",
    "811121": "Automotive Body, Paint and Interior Repair and Maintenance",
    "811122": "Automotive Glass Replacement Shops",
    "811192": "Car Washes",
    "811310": "Commercial and Industrial Machinery and Equipment (except Automotive and Electronic) Repair and Maintenance",
    "811411": "Home and Garden Equipment Repair and Maintenance",
    "811412": "Appliance Repair and Maintenance",
    "811420": "Reupholstery and Furniture Repair",
    "811430": "Footwear and Leather Goods Repair",
    "811490": "Other Personal and Household Goods Repair and Maintenance",
    "812210": "Funeral Homes",
    "812220": "Cemeteries and Crematoria",
    "812310": "Coin-Operated Laundries and Dry Cleaners",
    "812320": "Dry Cleaning and Laundry Services (except Coin-Operated)",
    "812910": "Pet Care (except Veterinary) Services",
    "812921": "Photo Finishing Laboratories (except One-Hour)",
    "812922": "One-Hour Photo Finishing",
    "812930": "Parking Lots and Garages",
    "812990": "All Other Personal Services",
    "813110": "Religious Organizations",
    "813410": "Civic and Social Organizations",
    "813910": "Business Associations",
    "813920": "Professional Organizations",
    "813930": "Labour Organizations",
    "813940": "Political Organizations",
    "813990": "Other Membership Organizations",
    "814110": "Private Households",
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

    # Handle TBD placeholder values from data sources
    if str(naics_code).strip().upper() in ["TBD", "TO BE DETERMINED", "N/A", "NA"]:
        return None

    # Clean the code - remove any non-digits
    clean_code = "".join(c for c in str(naics_code) if c.isdigit())

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
    clean_code = "".join(c for c in str(naics_code) if c.isdigit())

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
    clean_code = (
        "".join(c for c in str(naics_code) if c.isdigit()) if naics_code else ""
    )

    if len(clean_code) != 6:
        return {"code": naics_code, "description": None, "valid": False}

    description = NAICS_DESCRIPTIONS.get(clean_code)

    return {
        "code": clean_code,
        "description": description,
        "valid": description is not None,
    }
