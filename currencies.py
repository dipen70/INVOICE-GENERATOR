"""
Currency catalog. Pulls the live ISO 4217 list from the public
openexchangerates.org currency endpoint (no auth required) and merges it
with a bundled symbol map. Falls back to the bundled list offline.
"""
from __future__ import annotations

CURRENCY_API = "https://openexchangerates.org/api/currencies.json"
HTTP_TIMEOUT = 4

# Symbol map for common ISO 4217 codes. The API gives us names; we add symbols.
# Codes not in this map fall back to the code itself as the symbol.
SYMBOLS: dict[str, str] = {
    "USD": "$",   "EUR": "€",   "GBP": "£",   "INR": "₹",   "JPY": "¥",
    "CNY": "¥",   "CAD": "CA$", "AUD": "A$",  "CHF": "CHF", "NZD": "NZ$",
    "SGD": "S$",  "HKD": "HK$", "KRW": "₩",   "MXN": "MX$", "BRL": "R$",
    "RUB": "₽",   "ZAR": "R",   "TRY": "₺",   "AED": "د.إ", "SAR": "﷼",
    "THB": "฿",   "MYR": "RM",  "IDR": "Rp",  "PHP": "₱",   "VND": "₫",
    "EGP": "E£",  "NGN": "₦",   "KES": "KSh", "GHS": "GH₵", "NOK": "kr",
    "SEK": "kr",  "DKK": "kr",  "PLN": "zł",  "CZK": "Kč",  "HUF": "Ft",
    "ILS": "₪",   "ARS": "AR$", "CLP": "CL$", "COP": "CO$", "PEN": "S/",
    "UAH": "₴",   "PKR": "₨",   "BDT": "৳",   "LKR": "Rs",  "NPR": "रू",
    "ETB": "Br",  "MAD": "د.م.","TWD": "NT$", "RON": "lei", "BGN": "лв",
    "HRK": "kn",  "ISK": "kr",  "QAR": "﷼",   "KWD": "د.ك", "BHD": ".د.ب",
    "OMR": "﷼",   "JOD": "د.ا", "LBP": "ل.ل","DZD": "د.ج", "TND": "د.ت",
    "IQD": "ع.د", "IRR": "﷼",   "AFN": "؋",   "MMK": "K",   "KHR": "៛",
    "LAK": "₭",   "MNT": "₮",   "KZT": "₸",   "UZS": "лв",  "AZN": "₼",
    "GEL": "₾",   "AMD": "֏",   "BYN": "Br",  "MDL": "L",   "RSD": "дин",
    "MKD": "ден", "ALL": "L",   "BAM": "KM",  "BWP": "P",   "MUR": "₨",
    "NAD": "N$",  "TZS": "TSh", "UGX": "USh", "ZMW": "ZK",  "XOF": "CFA",
    "XAF": "FCFA","XPF": "₣",   "XCD": "EC$", "JMD": "J$",  "TTD": "TT$",
    "BBD": "Bds$","BSD": "B$",  "BZD": "BZ$", "DOP": "RD$", "GTQ": "Q",
    "HNL": "L",   "NIO": "C$",  "CRC": "₡",   "PAB": "B/.", "PYG": "₲",
    "UYU": "$U",  "BOB": "Bs.", "VEF": "Bs",  "VES": "Bs.S","SRD": "$",
    "GYD": "G$",  "FJD": "FJ$", "PGK": "K",   "SBD": "SI$", "TOP": "T$",
    "WST": "WS$", "VUV": "Vt",  "BTN": "Nu.", "MOP": "MOP$","BND": "B$",
    "MVR": "Rf",  "SCR": "₨",   "SLL": "Le",  "SLE": "Le",  "GMD": "D",
    "GNF": "FG",  "LRD": "L$",  "MGA": "Ar",  "MWK": "MK",  "MZN": "MT",
    "RWF": "FRw", "SOS": "Sh",  "SSP": "£",   "SDG": "ج.س.","DJF": "Fdj",
    "ERN": "Nfk", "KMF": "CF",  "LSL": "L",   "SZL": "L",   "BIF": "FBu",
    "CDF": "FC",  "AOA": "Kz",  "STN": "Db",  "CVE": "$",   "CUP": "$",
    "HTG": "G",   "AWG": "ƒ",   "ANG": "ƒ",   "KGS": "с",   "TJS": "ЅМ",
    "TMT": "T",
}

# Bundled fallback used when the API is unreachable. ~50 most-used currencies.
FALLBACK_CURRENCIES: dict[str, str] = {
    "USD": "United States Dollar",
    "EUR": "Euro",
    "GBP": "British Pound Sterling",
    "INR": "Indian Rupee",
    "JPY": "Japanese Yen",
    "CNY": "Chinese Yuan",
    "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar",
    "CHF": "Swiss Franc",
    "NZD": "New Zealand Dollar",
    "SGD": "Singapore Dollar",
    "HKD": "Hong Kong Dollar",
    "KRW": "South Korean Won",
    "MXN": "Mexican Peso",
    "BRL": "Brazilian Real",
    "RUB": "Russian Ruble",
    "ZAR": "South African Rand",
    "TRY": "Turkish Lira",
    "AED": "United Arab Emirates Dirham",
    "SAR": "Saudi Riyal",
    "THB": "Thai Baht",
    "MYR": "Malaysian Ringgit",
    "IDR": "Indonesian Rupiah",
    "PHP": "Philippine Peso",
    "VND": "Vietnamese Dong",
    "EGP": "Egyptian Pound",
    "NGN": "Nigerian Naira",
    "KES": "Kenyan Shilling",
    "NOK": "Norwegian Krone",
    "SEK": "Swedish Krona",
    "DKK": "Danish Krone",
    "PLN": "Polish Zloty",
    "CZK": "Czech Koruna",
    "HUF": "Hungarian Forint",
    "ILS": "Israeli Shekel",
    "ARS": "Argentine Peso",
    "CLP": "Chilean Peso",
    "COP": "Colombian Peso",
    "PEN": "Peruvian Sol",
    "UAH": "Ukrainian Hryvnia",
    "PKR": "Pakistani Rupee",
    "BDT": "Bangladeshi Taka",
    "LKR": "Sri Lankan Rupee",
    "TWD": "New Taiwan Dollar",
    "RON": "Romanian Leu",
    "QAR": "Qatari Riyal",
    "KWD": "Kuwaiti Dinar",
    "BHD": "Bahraini Dinar",
    "OMR": "Omani Rial",
    "JOD": "Jordanian Dinar",
}

_CACHE: dict[str, str] | None = None


def fetch_currencies() -> dict[str, str]:
    """Return {code: name}. Tries the live API once, then caches the result.
    On failure (no internet, request library missing, bad response) returns
    the bundled fallback list."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    try:
        import requests
        resp = requests.get(CURRENCY_API, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and len(data) > 20:
            _CACHE = data
            return _CACHE
    except Exception:
        pass

    _CACHE = dict(FALLBACK_CURRENCIES)
    return _CACHE


def symbol_for(code: str) -> str:
    """Symbol for an ISO code. Falls back to the code itself."""
    return SYMBOLS.get(code, code)


def display_options() -> list[str]:
    """List of dropdown labels, e.g. 'USD — United States Dollar ($)'.
    Sorted with major currencies first, then alphabetical."""
    currencies = fetch_currencies()
    priority = ["USD", "EUR", "GBP", "INR", "JPY", "CNY", "CAD", "AUD"]

    def label(code: str) -> str:
        name = currencies[code]
        sym = symbol_for(code)
        return f"{code} — {name} ({sym})"

    seen = set()
    ordered: list[str] = []
    for code in priority:
        if code in currencies:
            ordered.append(label(code))
            seen.add(code)
    for code in sorted(currencies):
        if code not in seen:
            ordered.append(label(code))
    return ordered


def code_from_label(label: str) -> str:
    """Pull the ISO code back out of a 'USD — ...' label."""
    return label.split(" — ", 1)[0].strip()
