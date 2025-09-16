"""
South African geographic data for address validation
"""

PROVINCES = {
    "Eastern Cape": {"code": "EC", "capital": "Bhisho", "major_cities": ["Port Elizabeth", "East London", "Mthatha", "Grahamstown", "Uitenhage"]},
    "Free State": {"code": "FS", "capital": "Bloemfontein", "major_cities": ["Bloemfontein", "Welkom", "Bethlehem", "Kroonstad", "Sasolburg"]},
    "Gauteng": {"code": "GP", "capital": "Johannesburg", "major_cities": ["Johannesburg", "Pretoria", "Soweto", "Centurion", "Sandton", "Randburg", "Midrand", "Benoni", "Krugersdorp", "Kempton Park"]},
    "KwaZulu-Natal": {"code": "KZN", "capital": "Pietermaritzburg", "major_cities": ["Durban", "Pietermaritzburg", "Newcastle", "Ladysmith", "Richards Bay", "Pinetown", "Umlazi", "Chatsworth"]},
    "Limpopo": {"code": "LP", "capital": "Polokwane", "major_cities": ["Polokwane", "Tzaneen", "Louis Trichardt", "Phalaborwa", "Mokopane"]},
    "Mpumalanga": {"code": "MP", "capital": "Mbombela", "major_cities": ["Mbombela", "Nelspruit", "Emalahleni", "Secunda", "Middelburg", "Standerton"]},
    "Northern Cape": {"code": "NC", "capital": "Kimberley", "major_cities": ["Kimberley", "Upington", "Springbok", "De Aar", "Kuruman"]},
    "North West": {"code": "NW", "capital": "Mahikeng", "major_cities": ["Mahikeng", "Rustenburg", "Klerksdorp", "Potchefstroom", "Brits"]},
    "Western Cape": {"code": "WC", "capital": "Cape Town", "major_cities": ["Cape Town", "Stellenbosch", "George", "Paarl", "Worcester", "Hermanus", "Knysna", "Mossel Bay", "Somerset West", "Bellville"]}
}

POSTAL_CODE_RANGES = {
    "Eastern Cape": [(4700, 6499)],
    "Free State": [(9300, 9999)],
    "Gauteng": [(1400, 1999), (2000, 2199)],
    "KwaZulu-Natal": [(2900, 4730)],
    "Limpopo": [(600, 999)],
    "Mpumalanga": [(1000, 1399), (2200, 2499)],
    "Northern Cape": [(8300, 8999)],
    "North West": [(2500, 2899)],
    "Western Cape": [(6500, 8299), (7000, 8099)]
}

SA_BOUNDS = {
    "lat_min": -34.83,
    "lat_max": -22.13,
    "lon_min": 16.45,
    "lon_max": 32.89
}

STREET_TYPES = ["Street", "Road", "Avenue", "Drive", "Lane", "Crescent", "Way", "Close", "Place", "Boulevard", "Highway", "Freeway"]

COMMON_SUBURBS = {
    "Cape Town": ["Sea Point", "Green Point", "Camps Bay", "Clifton", "Newlands", "Rondebosch", "Observatory", "Woodstock", "Salt River", "Mowbray", "Claremont", "Constantia", "Tokai", "Bergvliet", "Plumstead", "Wynberg", "Kenilworth", "Hout Bay", "Llandudno", "Fish Hoek", "Muizenberg", "Khayelitsha", "Mitchells Plain", "Gugulethu", "Langa"],
    "Johannesburg": ["Sandton", "Rosebank", "Melville", "Parktown", "Westcliff", "Houghton", "Illovo", "Hyde Park", "Morningside", "Rivonia", "Fourways", "Randburg", "Northcliff", "Auckland Park", "Braamfontein", "Hillbrow", "Yeoville", "Alexandra", "Soweto", "Lenasia", "Eldorado Park"],
    "Durban": ["Umhlanga", "Morningside", "Musgrave", "Berea", "Glenwood", "Overport", "Chatsworth", "Phoenix", "Umlazi", "KwaMashu", "Pinetown", "Westville", "Hillcrest", "Kloof", "Gillitts"],
    "Pretoria": ["Brooklyn", "Waterkloof", "Menlo Park", "Lynnwood", "Hatfield", "Arcadia", "Sunnyside", "Centurion", "Montana", "Wonderboom", "Gezina", "Menlyn", "Garsfontein", "Faerie Glen"],
    "Port Elizabeth": ["Summerstrand", "Humewood", "Walmer", "Mill Park", "Newton Park", "Parsons Hill", "Westering", "Lorraine", "Framesby", "Greenacres"],
    "Bloemfontein": ["Westdene", "Universitas", "Langenhoven Park", "Fichardt Park", "Pellissier", "Willows", "Dan Pienaar", "Heuwelsig"]
}

PROVINCE_CODES = {code: province for province, data in PROVINCES.items() for code in [data["code"]]}

COMMON_ABBREVIATIONS = {
    "st": "street",
    "str": "street",
    "rd": "road",
    "ave": "avenue",
    "dr": "drive",
    "ln": "lane",
    "ct": "court",
    "pl": "place",
    "blvd": "boulevard",
    "cres": "crescent",
    "apt": "apartment",
    "bldg": "building",
    "fl": "floor",
    "ste": "suite",
    "jhb": "johannesburg",
    "pta": "pretoria",
    "cpt": "cape town",
    "dbn": "durban",
    "pe": "port elizabeth",
    "oos-kaap": "eastern cape",
    "wes-kaap": "western cape",
    "noord-kaap": "northern cape"
}