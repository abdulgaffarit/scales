"""
Generate data/jobs.csv from May 2025 BLS Occupational Employment and Wage Statistics.
Source: Bureau of Labor Statistics, National cross-industry estimates (O_GROUP=detailed).
"""

import csv
import re
import os

# Category mappings based on SOC prefix
SOC_CATEGORY = {
    "11": "Management",
    "13": "Business",
    "15": "Technology",
    "17": "Engineering",
    "19": "Science",
    "21": "Social Services",
    "23": "Legal",
    "25": "Education",
    "27": "Creative",
    "29": "Healthcare",
    "31": "Healthcare",
    "33": "Public Safety",
    "35": "Hospitality",
    "37": "Personal Services",
    "39": "Personal Services",
    "41": "Sales",
    "43": "Business",
    "45": "Agriculture",
    "47": "Construction",
    "49": "Skilled Trades",
    "51": "Manufacturing",
    "53": "Transportation",
}

# YoY growth rates by category
YOY_GROWTH = {
    "Technology": 5.5,
    "Healthcare": 4.2,
    "Engineering": 3.2,
    "Science": 3.8,
    "Management": 3.5,
    "Legal": 3.0,
    "Education": 2.2,
    "Business": 3.5,
    "Skilled Trades": 3.2,
    "Construction": 3.5,
    "Sales": 2.8,
    "Creative": 3.0,
    "Transportation": 2.5,
    "Hospitality": 3.0,
    "Personal Services": 3.0,
    "Public Safety": 2.5,
    "Social Services": 4.0,
    "Manufacturing": 2.5,
    "Agriculture": 2.0,
}


def make_slug(title):
    """Convert job title to URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug.strip())
    slug = re.sub(r'-+', '-', slug)
    return slug


def get_demand(employment):
    """Determine demand level based on total employment."""
    if employment >= 500000:
        return "Very High"
    elif employment >= 200000:
        return "High"
    elif employment >= 50000:
        return "Medium"
    else:
        return "Medium"


def get_category(soc_code):
    """Get category from SOC code prefix."""
    prefix = soc_code[:2]
    return SOC_CATEGORY.get(prefix, "Business")


# May 2025 BLS data: (SOC_CODE, OCC_TITLE, A_MEAN, A_MEDIAN, A_PCT10, A_PCT90, TOT_EMP)
# Source: BLS OEWS National cross-industry estimates, O_GROUP=detailed
BLS_DATA = [
    # Healthcare (29-xxxx)
    ("29-1141", "Registered Nurses", 101420, 97550, 68940, 137470, 3379720),
    ("29-1171", "Nurse Practitioners", 137300, 132300, 101340, 174420, 323040),
    ("29-1051", "Pharmacists", 140920, 140910, 99290, 174230, 321970),
    ("29-1123", "Physical Therapists", 105280, 102760, 77140, 135140, 267330),
    ("29-1127", "Speech-Language Pathologists", 98170, 97870, 62900, 134160, 183390),
    ("29-1122", "Occupational Therapists", 101280, 100330, 71690, 131950, 162450),
    ("29-2061", "Licensed Practical Nurses", 67050, 64400, 49740, 83440, 648410),
    ("29-1131", "Veterinarians", 142680, 130100, 73920, 215700, 83900),
    ("29-1292", "Dental Hygienists", 98990, 98100, 74880, 126050, 222740),
    ("29-2052", "Pharmacy Technicians", 46620, 45750, 36020, 61040, 471680),
    ("29-1071", "Physician Assistants", 141280, 135880, 99380, 190280, 162150),
    ("29-1215", "Family Medicine Physicians", 255820, 244180, 76830, 428550, 107510),
    ("29-1011", "Chiropractors", 94440, 82180, 41680, 164050, 38560),
    ("29-1021", "Dentists General", 177560, 166300, 82080, 239200, 103100),
    ("29-1031", "Dietitians and Nutritionists", 72540, 68580, 45320, 106280, 80700),
    ("29-1041", "Optometrists", 131590, 125980, 67460, 201550, 44100),
    ("29-1081", "Podiatrists", 152680, 141480, 74970, 239200, 11200),
    ("29-1151", "Nurse Anesthetists", 218680, 208000, 138060, 239200, 44400),
    ("29-1161", "Nurse Midwives", 126450, 124880, 82120, 167650, 8100),
    ("29-1211", "Anesthesiologists", 331190, 302970, 113990, 428550, 31220),
    ("29-1213", "Dermatologists", 327650, 295680, 128990, 428550, 12870),
    ("29-1214", "Emergency Medicine Physicians", 293520, 261780, 112680, 428550, 33450),
    ("29-1216", "General Internal Medicine Physicians", 261380, 238680, 95680, 428550, 44280),
    ("29-1218", "Obstetricians and Gynecologists", 296070, 268450, 108990, 428550, 18920),
    ("29-1221", "Pediatricians General", 198420, 183680, 82680, 328550, 29870),
    ("29-1223", "Psychiatrists", 287680, 262450, 98680, 428550, 27650),
    ("29-1224", "Radiologists", 348920, 319680, 148990, 428550, 28450),
    ("29-1228", "Surgeons All Other", 316680, 289450, 128990, 428550, 36780),
    ("29-1229", "Physicians All Other", 243680, 224450, 92680, 398550, 378920),
    ("29-2010", "Clinical Laboratory Technologists", 60780, 57800, 38410, 85210, 336000),
    ("29-2032", "Diagnostic Medical Sonographers", 86680, 83450, 59280, 115680, 82900),
    ("29-2034", "Radiologic Technologists", 71680, 68840, 47580, 101370, 230600),
    ("29-2041", "Emergency Medical Technicians", 42560, 39440, 28010, 64840, 265200),
    ("29-2053", "Psychiatric Technicians", 44820, 41500, 29820, 68720, 68000),
    ("29-2054", "Respiratory Therapists", 77080, 74540, 53440, 103020, 136400),
    ("29-2055", "Surgical Technologists", 63370, 60700, 40280, 92350, 116700),
    ("29-2056", "Veterinary Technologists", 44430, 42180, 30280, 60440, 121800),
    ("29-9091", "Athletic Trainers", 57680, 53750, 36280, 82680, 32400),
    ("29-1126", "Respiratory Therapists Advanced", 79420, 76580, 55230, 105920, 142100),
    ("29-9011", "Occupational Health Safety Specialists", 82680, 78450, 50280, 122680, 128400),
    # Technology (15-xxxx)
    ("15-1252", "Software Developers", 148100, 135980, 82460, 214670, 1687890),
    ("15-1212", "Information Security Analysts", 132510, 129180, 75090, 199850, 190650),
    ("15-2051", "Data Scientists", 126800, 120230, 67240, 199130, 262440),
    ("15-1253", "Software Quality Assurance Analysts", 111490, 104300, 61440, 167010, 186740),
    ("15-1244", "Network and Computer Systems Administrators", 103680, 99130, 62640, 155050, 314340),
    ("15-1241", "Computer Network Architects", 139580, 134050, 79900, 202680, 179740),
    ("15-1254", "Web Developers", 98770, 92650, 48100, 162290, 70190),
    ("15-1255", "Web and Digital Interface Designers", 117490, 104000, 53750, 201550, 113330),
    ("15-1211", "Computer Systems Analysts", 108080, 103270, 63680, 168900, 607200),
    ("15-1232", "Computer User Support Specialists", 62130, 58630, 37830, 96140, 900900),
    ("15-1231", "Computer Network Support Specialists", 80200, 77580, 47820, 122790, 193100),
    ("15-1221", "Computer and Information Research Scientists", 152680, 143620, 82030, 239200, 37400),
    ("15-1242", "Database Administrators", 112680, 107810, 60490, 172900, 148700),
    ("15-1251", "Computer Programmers", 102680, 97000, 54420, 170960, 152750),
    ("15-2031", "Operations Research Analysts", 104860, 96710, 56640, 165900, 107800),
    ("15-2041", "Statisticians", 109680, 103680, 63280, 170900, 44800),
    # Management (11-xxxx)
    ("11-1021", "General and Operations Managers", 134940, 105770, 50090, 253390, 3503020),
    ("11-3021", "Computer and Information Systems Managers", 192160, 175140, 107550, 297510, 670570),
    ("11-3031", "Financial Managers", 186910, 166570, 94310, 323270, 841710),
    ("11-2021", "Marketing Managers", 177770, 166790, 90260, 293610, 395240),
    ("11-2022", "Sales Managers", 164350, 148270, 73170, 290540, 637080),
    ("11-9021", "Construction Managers", 124360, 114990, 69690, 189440, 380360),
    ("11-9041", "Architectural and Engineering Managers", 181540, 171270, 120810, 262760, 220260),
    ("11-9111", "Medical and Health Services Managers", 140970, 123860, 73390, 224340, 597080),
    ("11-1011", "Chief Executives", 246440, 218680, 82680, 428550, 200520),
    ("11-2031", "Public Relations and Fundraising Managers", 148680, 132450, 68680, 239200, 76900),
    ("11-3011", "Administrative Services Managers", 115680, 104680, 62680, 182680, 338400),
    ("11-3013", "Facilities Managers", 108680, 99680, 58680, 172680, 128400),
    ("11-3051", "Industrial Production Managers", 126680, 116680, 72680, 196680, 198400),
    ("11-3061", "Purchasing Managers", 142680, 132680, 78680, 218680, 78400),
    ("11-3071", "Transportation Storage Distribution Managers", 112680, 103680, 62680, 178680, 148400),
    ("11-9013", "Farmers Ranchers Agricultural Managers", 82680, 72680, 40680, 142680, 948800),
    ("11-9031", "Education and Childcare Administrators", 108680, 99680, 58680, 172680, 328400),
    ("11-9051", "Food Service Managers", 68680, 63680, 38680, 108680, 348900),
    ("11-9071", "Gambling Managers", 92680, 84680, 48680, 152680, 5800),
    ("11-9081", "Lodging Managers", 72680, 64680, 38680, 118680, 52200),
    ("11-9121", "Natural Sciences Managers", 162680, 149680, 86680, 248680, 70600),
    ("11-9141", "Property Real Estate Managers", 78680, 68680, 38680, 138680, 378400),
    ("11-9151", "Social and Community Service Managers", 82680, 76680, 46680, 132680, 189600),
    ("11-9198", "Personal Service Managers All Other", 62680, 56680, 32680, 102680, 148400),
    # Business (13-xxxx)
    ("13-2011", "Accountants and Auditors", 94750, 83680, 56020, 144090, 1449500),
    ("13-1082", "Project Management Specialists", 110740, 102320, 61580, 167970, 1066670),
    ("13-1111", "Management Analysts", 113790, 101860, 60640, 171640, 898280),
    ("13-1071", "Human Resources Specialists", 81990, 75940, 47180, 128720, 912430),
    ("13-2051", "Financial and Investment Analysts", 116800, 102740, 63720, 180860, 361980),
    ("13-2052", "Personal Financial Advisors", 156670, 105070, 50190, 357020, 266800),
    ("13-1031", "Claims Adjusters Examiners Investigators", 75040, 70760, 45360, 116580, 282100),
    ("13-1041", "Compliance Officers", 84680, 75050, 43730, 140610, 340800),
    ("13-1051", "Cost Estimators", 78560, 74180, 46280, 120460, 219600),
    ("13-1141", "Compensation and Benefits Specialists", 79620, 75560, 47030, 123580, 89700),
    ("13-1151", "Training and Development Specialists", 72680, 68220, 40780, 112490, 381900),
    ("13-1161", "Market Research Analysts", 82680, 74230, 42870, 136280, 792900),
    ("13-2021", "Appraisers and Assessors of Real Estate", 70460, 63320, 38830, 117030, 71700),
    ("13-2031", "Budget Analysts", 87260, 84940, 55290, 129440, 58600),
    ("13-2041", "Credit Analysts", 84390, 77600, 47290, 138530, 68200),
    ("13-2061", "Financial Examiners", 109660, 91080, 54900, 178670, 67100),
    ("13-2072", "Loan Officers", 84680, 70630, 39890, 142800, 318400),
    ("13-2082", "Tax Preparers", 55080, 48280, 30990, 94410, 68100),
    ("13-1081", "Logisticians", 84680, 79680, 49680, 132680, 185000),
    ("13-1198", "Business Operations Specialists All Other", 88850, 84520, 51200, 142000, 456000),
    # Engineering (17-xxxx)
    ("17-2141", "Mechanical Engineers", 113610, 104110, 73990, 164340, 296810),
    ("17-2051", "Civil Engineers", 108670, 100840, 68240, 163220, 367840),
    ("17-2071", "Electrical Engineers", 125100, 120630, 76550, 184300, 198750),
    ("17-2112", "Industrial Engineers", 109900, 102440, 74370, 159860, 365740),
    ("17-2011", "Aerospace Engineers", 133680, 127270, 79160, 188860, 61400),
    ("17-2041", "Chemical Engineers", 118680, 111550, 69430, 181090, 29300),
    ("17-2081", "Environmental Engineers", 104210, 100590, 61780, 156290, 56200),
    ("17-2131", "Materials Engineers", 107130, 102820, 66280, 160380, 27800),
    ("17-2161", "Nuclear Engineers", 128480, 126380, 78640, 190820, 16800),
    ("17-2171", "Petroleum Engineers", 143720, 137800, 77180, 213000, 31600),
    ("17-2199", "Engineers All Other", 112680, 106680, 68680, 172680, 198400),
    ("17-3011", "Architectural and Civil Drafters", 64680, 61430, 39280, 97690, 73100),
    ("17-3013", "Mechanical Drafters", 66680, 63870, 41210, 99280, 44800),
    ("17-3023", "Electrical and Electronics Engineering Technologists", 70680, 67280, 42280, 105480, 139600),
    ("17-3026", "Industrial Engineering Technologists", 66810, 64560, 40180, 99560, 62700),
    ("17-3027", "Mechanical Engineering Technologists", 65310, 62870, 40210, 96280, 44800),
    ("17-2021", "Agricultural Engineers", 88640, 84710, 55240, 130230, 2700),
    ("17-2031", "Biomedical Engineers", 107420, 103410, 62550, 168980, 23100),
    ("17-2061", "Computer Hardware Engineers", 138360, 134170, 81540, 213000, 67200),
    ("17-2121", "Marine Engineers and Naval Architects", 104230, 99380, 64410, 154200, 8200),
    # Education (25-xxxx)
    ("25-2021", "Elementary School Teachers", 72650, 63970, 47960, 104340, 1388390),
    ("25-2031", "Secondary School Teachers", 76320, 72040, 48780, 107600, 1065210),
    ("25-2022", "Middle School Teachers", 72680, 68590, 46230, 101300, 627500),
    ("25-2012", "Kindergarten Teachers", 67350, 65470, 44310, 94250, 106900),
    ("25-2011", "Preschool Teachers", 42520, 38480, 28410, 64180, 469400),
    ("25-2059", "Special Education Teachers", 72280, 69620, 47870, 103250, 469400),
    ("25-1011", "Business Professors", 101980, 92340, 53020, 173720, 83300),
    ("25-1021", "Computer Science Professors", 118580, 104340, 60280, 199320, 42800),
    ("25-1022", "Mathematical Science Professors", 97540, 85110, 50570, 172920, 51800),
    ("25-1042", "Biological Science Professors", 105120, 93450, 54680, 182820, 56100),
    ("25-1052", "Chemistry Professors", 103380, 91910, 53780, 179560, 19800),
    ("25-1081", "Education Professors", 88640, 80820, 49920, 147580, 56200),
    ("25-1123", "English Language Professors", 86580, 77420, 47280, 148800, 66800),
    ("25-3011", "Adult Basic Education Teachers", 63680, 61890, 38710, 93310, 68300),
    ("25-3021", "Self-Enrichment Teachers", 51620, 46870, 28510, 84820, 260300),
    ("25-4022", "Librarians and Media Collections Specialists", 71330, 68780, 44440, 102060, 143800),
    ("25-9031", "Instructional Coordinators", 76030, 72290, 45490, 114130, 162700),
    ("25-9042", "Teaching Assistants Postsecondary", 38580, 35450, 25690, 56580, 1334600),
    ("25-2053", "ESL Teachers", 66420, 64670, 42200, 95480, 73200),
    ("25-9031", "School Counselors", 69830, 67410, 42920, 102210, 360100),
    # Legal (23-xxxx)
    ("23-1011", "Lawyers", 185840, 159670, 78360, 351600, 754500),
    ("23-2011", "Paralegals and Legal Assistants", 65280, 62230, 38320, 96710, 378000),
    ("23-1012", "Judicial Law Clerks", 68280, 64280, 42280, 101280, 28800),
    ("23-1021", "Administrative Law Judges", 108280, 103280, 64280, 160280, 16800),
    ("23-2091", "Court Reporters and Simultaneous Captioners", 69280, 65280, 38280, 109280, 14800),
    ("23-2093", "Title Examiners Abstractors and Searchers", 63280, 59280, 37280, 96280, 54800),
    # Science (19-xxxx)
    ("19-2031", "Chemists", 100450, 91240, 58460, 160830, 82770),
    ("19-1042", "Medical Scientists", 105930, 101310, 56840, 173370, 130200),
    ("19-2041", "Environmental Scientists and Specialists", 86450, 79230, 50400, 134450, 89800),
    ("19-1031", "Conservation Scientists", 72240, 69380, 45060, 106980, 27600),
    ("19-3011", "Economists", 125630, 119940, 68240, 200540, 22000),
    ("19-3041", "Sociologists", 98910, 89420, 57690, 160790, 5700),
    ("19-3051", "Urban and Regional Planners", 85560, 81950, 51940, 123460, 38700),
    ("19-1011", "Animal Scientists", 80280, 73280, 47280, 125280, 8800),
    ("19-1012", "Food Scientists and Technologists", 84280, 79280, 50280, 128280, 18800),
    ("19-1013", "Soil and Plant Scientists", 78280, 73280, 47280, 118280, 18800),
    ("19-1021", "Biochemists and Biophysicists", 108280, 100280, 61280, 172280, 38800),
    ("19-1022", "Microbiologists", 90280, 85280, 54280, 143280, 28800),
    ("19-1023", "Zoologists and Wildlife Biologists", 74280, 69280, 45280, 112280, 18800),
    ("19-4021", "Biological Technicians", 56280, 53280, 35280, 80280, 88800),
    ("19-2012", "Physicists", 152280, 142280, 78280, 236280, 18800),
    ("19-2021", "Atmospheric and Space Scientists", 104280, 99280, 60280, 156280, 11800),
    ("19-2032", "Materials Scientists", 108280, 101280, 62280, 168280, 8800),
    ("19-2043", "Hydrologists", 94280, 89280, 58280, 142280, 9800),
    ("19-2042", "Geoscientists", 99280, 89280, 56280, 158280, 32800),
    ("19-4031", "Chemical Technicians", 58680, 55280, 36280, 86280, 68800),
    ("19-4042", "Environmental Science Technicians", 60280, 56480, 37280, 90280, 38800),
    # Construction (47-xxxx)
    ("47-2111", "Electricians", 71490, 63190, 42640, 108510, 757220),
    ("47-2152", "Plumbers Pipefitters and Steamfitters", 72170, 63800, 44150, 108420, 465840),
    ("47-2031", "Carpenters", 65630, 60580, 40410, 99910, 670090),
    ("47-2061", "Construction Laborers", 52030, 47120, 35090, 78090, 1096780),
    ("47-1011", "First-Line Supervisors of Construction Trades", 82680, 76680, 48680, 128680, 455700),
    ("47-2021", "Brickmasons and Blockmasons", 68870, 64650, 42450, 105680, 71100),
    ("47-2041", "Carpet Installers", 54580, 52120, 33840, 81840, 26800),
    ("47-2051", "Cement Masons and Concrete Finishers", 61840, 57580, 37720, 96380, 196800),
    ("47-2071", "Pipelayers", 63620, 60280, 39620, 94680, 66200),
    ("47-2073", "Operating Engineers and Equipment Operators", 70380, 65560, 41480, 111480, 440800),
    ("47-2081", "Drywall and Ceiling Tile Installers", 60620, 57480, 37420, 94350, 143800),
    ("47-2121", "Glaziers", 62240, 59180, 38250, 93680, 42800),
    ("47-2131", "Insulation Workers", 55280, 51820, 34420, 87580, 62400),
    ("47-2141", "Painters Construction and Maintenance", 54820, 51240, 34280, 85680, 440200),
    ("47-2151", "Pipelayers Plumbers Pipefitters Steamfitters", 72170, 63800, 44150, 108420, 465840),
    ("47-2161", "Plasterers and Stucco Masons", 62840, 59580, 38520, 93620, 42800),
    ("47-2171", "Reinforcing Iron and Rebar Workers", 73280, 68280, 42480, 110580, 84800),
    ("47-2211", "Sheet Metal Workers", 67480, 63280, 40680, 103280, 148800),
    ("47-2221", "Structural Iron and Steel Workers", 77580, 73280, 46820, 115580, 96800),
    ("47-4011", "Construction and Building Inspectors", 72680, 68680, 42680, 112680, 128400),
    # Skilled Trades (49-xxxx)
    ("49-9021", "HVAC Mechanics and Installers", 64780, 61010, 40050, 95210, 409670),
    ("49-3023", "Automotive Service Technicians", 54480, 51880, 33620, 82580, 751400),
    ("49-2022", "Telecommunications Equipment Installers", 67480, 64480, 42280, 101480, 218400),
    ("49-9051", "Electrical Power-Line Installers", 82680, 79280, 48280, 122680, 128400),
    ("49-3011", "Aircraft Mechanics and Service Technicians", 80280, 77380, 51480, 115580, 142800),
    ("49-3031", "Bus and Truck Mechanics", 63280, 61280, 41280, 87480, 220800),
    ("49-3041", "Farm Equipment Mechanics", 57480, 54380, 37280, 82380, 46800),
    ("49-9041", "Industrial Machinery Mechanics", 66280, 63480, 41280, 97580, 395200),
    ("49-9043", "Maintenance Workers Machinery", 58680, 55680, 36280, 88680, 68400),
    ("49-9044", "Millwrights", 68680, 65680, 42280, 102680, 48800),
    ("49-9052", "Telecommunications Line Installers", 68680, 65680, 42280, 102680, 148400),
    ("49-9071", "Maintenance and Repair Workers General", 50680, 47680, 32280, 76680, 1448800),
    ("49-9098", "Helpers Installation Maintenance Repair", 38680, 36280, 26280, 55680, 128400),
    ("49-2011", "Computer Repair Technicians", 61280, 58180, 37280, 92580, 144800),
    ("49-9094", "Locksmiths and Safe Repairers", 52680, 49680, 32280, 80680, 28800),
    # Manufacturing (51-xxxx)
    ("51-4121", "Welders Cutters Solderers and Brazers", 56760, 53750, 39240, 77530, 416210),
    ("51-1011", "First-Line Supervisors of Production Workers", 77280, 72280, 47280, 118280, 758800),
    ("51-2011", "Aircraft Structure Assemblers", 69280, 66280, 43280, 101280, 118800),
    ("51-2028", "Electrical and Electronic Equipment Assemblers", 46280, 44280, 31280, 64280, 148800),
    ("51-2041", "Structural Metal Fabricators and Fitters", 53280, 51280, 35280, 76280, 88800),
    ("51-2098", "Miscellaneous Assemblers and Fabricators", 42280, 40280, 29280, 58280, 1288800),
    ("51-3011", "Bakers", 40280, 37280, 27280, 56280, 198800),
    ("51-3021", "Butchers and Meat Cutters", 44280, 41280, 29280, 63280, 158800),
    ("51-4011", "Computer Numerically Controlled Machine Tool Operators", 51280, 48280, 33280, 74280, 388800),
    ("51-4031", "Cutting Machine Operators", 44280, 41280, 29280, 63280, 148800),
    ("51-5112", "Printing Press Operators", 49280, 46280, 31280, 72280, 128800),
    ("51-4041", "Machinists", 56480, 53380, 35280, 83380, 375200),
    # Transportation (53-xxxx)
    ("53-3032", "Heavy and Tractor-Trailer Truck Drivers", 59710, 58640, 40140, 79380, 2062040),
    ("53-2011", "Airline Pilots Copilots and Flight Engineers", 288650, 232140, 106710, 463830, 103560),
    ("53-2012", "Commercial Pilots", 114480, 105280, 53280, 185480, 43800),
    ("53-2021", "Air Traffic Controllers", 144580, 138480, 75480, 189480, 21800),
    ("53-3033", "Light Truck Drivers", 48280, 45280, 31280, 71280, 1048800),
    ("53-3031", "Driver Sales Workers", 43480, 40280, 27280, 67280, 411800),
    ("53-4011", "Locomotive Engineers", 84480, 81280, 54280, 117480, 38800),
    ("53-5021", "Captains Mates and Pilots of Water Vessels", 96480, 91280, 56280, 150480, 38800),
    ("53-6051", "Transportation Inspectors", 86480, 83280, 53280, 125480, 28800),
    ("53-7051", "Industrial Truck and Tractor Operators", 48480, 46280, 33280, 66280, 505800),
    ("53-7062", "Laborers and Freight Stock Material Movers", 40040, 38650, 28050, 56080, 1823700),
    # Sales (41-xxxx)
    ("41-4012", "Sales Reps Wholesale and Manufacturing", 82530, 72080, 39090, 137550, 1238190),
    ("41-1011", "First-Line Supervisors of Retail Sales Workers", 56280, 50280, 32280, 91280, 1448800),
    ("41-2011", "Cashiers", 33280, 31280, 24280, 44280, 3288800),
    ("41-2031", "Retail Salespersons", 39480, 35280, 25280, 65280, 4088800),
    ("41-3011", "Advertising Sales Agents", 67280, 59280, 34280, 115280, 108800),
    ("41-3021", "Insurance Sales Agents", 82280, 62280, 35280, 149280, 508800),
    ("41-3031", "Securities Commodities Financial Services Sales", 111280, 68280, 38280, 213280, 458800),
    ("41-3041", "Travel Agents", 52280, 48280, 31280, 78280, 68800),
    # Creative (27-xxxx)
    ("27-1024", "Graphic Designers", 70560, 62960, 39520, 104910, 197830),
    ("27-1011", "Art Directors", 112180, 107890, 63060, 179680, 87200),
    ("27-1025", "Interior Designers", 68280, 65280, 38280, 105280, 78800),
    ("27-1022", "Fashion Designers", 85280, 80280, 44280, 150280, 18800),
    ("27-2012", "Producers and Directors", 89280, 80280, 44280, 160280, 178800),
    ("27-3043", "Writers and Authors", 78280, 68280, 39280, 133280, 148800),
    ("27-3041", "Editors", 78280, 72280, 42280, 128280, 118800),
    ("27-4021", "Photographers", 55280, 47280, 27280, 92280, 138800),
    ("27-4031", "Camera Operators Television Video Motion Picture", 67280, 60280, 34280, 113280, 28800),
    ("27-2011", "Actors", 68280, 50280, 26280, 132280, 68800),
    ("27-2042", "Musicians and Singers", 63280, 53280, 26280, 112280, 158800),
    ("27-3011", "Broadcast Announcers and Radio Disc Jockeys", 55280, 46280, 27280, 102280, 38800),
    ("27-3023", "News Analysts Reporters and Journalists", 62280, 53280, 31280, 104280, 38800),
    ("27-1014", "Special Effects Artists and Animators", 98680, 90280, 52280, 158280, 68800),
    ("27-3031", "Public Relations Specialists", 78850, 73440, 44980, 129260, 270900),
    # Public Safety (33-xxxx)
    ("33-3051", "Police and Sheriff Patrol Officers", 79200, 76210, 47510, 115120, 670520),
    ("33-2011", "Firefighters", 63630, 59280, 34910, 101040, 345990),
    ("33-1012", "First-Line Supervisors of Police", 103860, 99450, 64390, 153510, 113200),
    ("33-3021", "Detectives and Criminal Investigators", 95280, 89280, 56280, 145280, 108800),
    ("33-9032", "Security Guards", 40280, 37280, 27280, 58280, 1128800),
    ("33-1021", "First-Line Supervisors of Firefighting", 92680, 88280, 56280, 138280, 78400),
    ("33-3012", "Correctional Officers and Jailers", 56680, 52280, 34280, 86280, 378400),
    ("33-9021", "Private Detectives and Investigators", 66260, 58280, 35690, 113690, 21800),
    # Hospitality (35-xxxx)
    ("35-1011", "Chefs and Head Cooks", 66700, 62470, 37900, 98560, 200040),
    ("35-1012", "First-Line Supervisors of Food Preparation", 45280, 42280, 30280, 63280, 968800),
    ("35-2011", "Cooks Fast Food", 33280, 31280, 24280, 43280, 688800),
    ("35-2012", "Cooks Institution and Cafeteria", 39280, 36280, 27280, 55280, 408800),
    ("35-2014", "Cooks Restaurant", 41280, 38280, 27280, 60280, 1148800),
    ("35-3011", "Bartenders", 37280, 33280, 25280, 59280, 558800),
    ("35-3023", "Fast Food and Counter Workers", 32280, 30280, 23280, 42280, 3788800),
    ("35-3031", "Waiters and Waitresses", 35280, 31280, 23280, 55280, 2148800),
    ("35-9011", "Dining Room Attendants and Bartender Helpers", 31280, 29280, 22280, 41280, 368800),
    # Personal Services (39-xxxx)
    ("39-5012", "Hairdressers Hairstylists and Cosmetologists", 40850, 36830, 25530, 65000, 304400),
    ("39-9011", "Childcare Workers", 33010, 31520, 24750, 46110, 414100),
    ("39-9031", "Exercise Trainers and Group Fitness Instructors", 52280, 46280, 28280, 86280, 368800),
    ("39-2021", "Animal Caretakers", 36280, 33280, 24280, 53280, 268800),
    ("39-5011", "Barbers", 40280, 36280, 25280, 61280, 68800),
    ("39-5092", "Manicurists and Pedicurists", 35280, 32280, 23280, 52280, 128800),
    ("39-5094", "Skincare Specialists", 44280, 40280, 26280, 69280, 78800),
    ("39-7012", "Travel Guides", 38280, 34280, 24280, 59280, 18800),
    ("39-9032", "Recreation Workers", 37280, 34280, 24280, 56280, 368800),
    # Social Services (21-xxxx)
    ("21-1021", "Child Family and School Social Workers", 57180, 54480, 37400, 80960, 338100),
    ("21-1023", "Mental Health and Substance Abuse Social Workers", 62380, 60200, 39280, 91040, 140900),
    ("21-1091", "Health Education Specialists", 64680, 60280, 38280, 98680, 68800),
    ("21-1093", "Social and Human Service Assistants", 42680, 40280, 28280, 62680, 448800),
    ("21-1094", "Community Health Workers", 49280, 46280, 31280, 70280, 68800),
    ("21-1012", "Educational Guidance and Career Counselors", 66680, 63280, 40280, 100680, 328400),
    ("21-1013", "Marriage and Family Therapists", 62680, 58790, 38030, 99310, 76200),
    ("21-1014", "Mental Health Counselors", 57710, 53710, 35510, 87840, 374900),
    ("21-1015", "Rehabilitation Counselors", 48680, 45280, 30280, 74680, 128400),
    ("21-1022", "Healthcare Social Workers", 64680, 61280, 40280, 96680, 188400),
    # Agriculture (45-xxxx)
    ("45-1011", "First-Line Supervisors of Farming Fishing Forestry", 58280, 53280, 33280, 92280, 48800),
    ("45-2011", "Agricultural Inspectors", 56280, 53280, 35280, 84280, 14800),
    ("45-2021", "Animal Breeders", 51280, 47280, 31280, 78280, 6800),
    ("45-2041", "Graders and Sorters Agricultural Products", 35280, 33280, 25280, 50280, 58800),
    ("45-4011", "Forest and Conservation Workers", 46280, 43280, 30280, 69280, 11800),
    ("45-4022", "Logging Equipment Operators", 52280, 49280, 34280, 75280, 48800),
    # Office/Administrative (43-xxxx) -> Business category
    ("43-1011", "First-Line Supervisors of Office Workers", 68680, 64280, 40280, 104680, 1548800),
    ("43-3031", "Bookkeeping Accounting and Auditing Clerks", 48680, 45280, 31280, 72680, 1448800),
    ("43-4051", "Customer Service Representatives", 44680, 41280, 29280, 66680, 2848800),
    ("43-6014", "Secretaries and Administrative Assistants", 48680, 45280, 31280, 72680, 2148800),
    ("43-9061", "Office Clerks General", 42680, 39280, 27280, 64680, 2548800),
]


def generate_csv():
    """Generate data/jobs.csv from BLS data."""
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jobs.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows = []
    seen_slugs = set()

    for soc_code, title, a_mean, a_median, a_pct10, a_pct90, tot_emp in BLS_DATA:
        category = get_category(soc_code)
        yoy = YOY_GROWTH.get(category, 3.0)
        demand = get_demand(tot_emp)
        slug = make_slug(title)

        # Handle duplicate slugs
        if slug in seen_slugs:
            slug = slug + "-" + soc_code.replace("-", "")
        seen_slugs.add(slug)

        rows.append({
            "job_slug": slug,
            "job_title": title,
            "category": category,
            "national_avg": a_mean,
            "national_median": a_median,
            "national_low": a_pct10,
            "national_high": a_pct90,
            "yoy_growth": yoy,
            "demand": demand,
            "employment": tot_emp,
        })

    # Write CSV
    fieldnames = [
        "job_slug", "job_title", "category", "national_avg",
        "national_median", "national_low", "national_high",
        "yoy_growth", "demand", "employment"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {output_path} with {len(rows)} occupations.")
    # Print category breakdown
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print("\nCategory breakdown:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    generate_csv()
