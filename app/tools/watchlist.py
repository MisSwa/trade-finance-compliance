"""
Mock sanctions watchlist data.

All entity names, vessel names, countries, and ports are fictional.
They are inspired by FATF TBML typology categories and do not correspond
to any real sanctioned person, company, vessel, or jurisdiction.
"""

_SANCTIONED_ENTITIES: dict[str, str] = {
    "Zarkon Trading Corporation": "critical",
    "Pacific Rim Commodities Ltd": "critical",
    "Northern Star Shipping LLC": "high",
    "Meridian Export House": "high",
    "Crescent Moon Trading Co": "high",
    "Atlas Global Freight Partners": "medium",
    "Dawnlight Procurement Services": "medium",
}

_SANCTIONED_VESSELS: dict[str, str] = {
    "MV Phantom Star": "critical",
    "SS Iron Eagle": "high",
    "MV Desert Wind": "high",
    "MV Shadow Runner": "medium",
}

_HIGH_RISK_COUNTRIES: set[str] = {
    "Ruritania",
    "Kravonia",
    "Bortovia",
    "Zandaria",
    "Mordavia",
}

_HIGH_RISK_PORTS: set[str] = {
    "Port Obscura",
    "Darkwater Terminal",
    "Shadow Bay",
    "Freeport Noctis",
}

_PROHIBITED_GOODS_KEYWORDS: list[str] = [
    "weapons components",
    "dual-use electronics",
    "precursor chemicals",
    "nuclear materials",
    "ballistic missile",
    "military explosives",
    "chemical weapon",
]


def check_entity(name: str) -> dict:
    name_lower = name.lower()
    for entity, severity in _SANCTIONED_ENTITIES.items():
        if entity.lower() == name_lower:
            return {"hit": True, "severity": severity, "match": entity}
    return {"hit": False, "severity": "none", "match": None}


def check_vessel(name: str) -> dict:
    name_lower = name.lower()
    for vessel, severity in _SANCTIONED_VESSELS.items():
        if vessel.lower() == name_lower:
            return {"hit": True, "severity": severity, "match": vessel}
    return {"hit": False, "severity": "none", "match": None}


def check_country(name: str) -> dict:
    for country in _HIGH_RISK_COUNTRIES:
        if country.lower() == name.lower():
            return {"hit": True, "severity": "high", "match": country}
    return {"hit": False, "severity": "none", "match": None}


def check_port(name: str) -> dict:
    for port in _HIGH_RISK_PORTS:
        if port.lower() == name.lower():
            return {"hit": True, "severity": "high", "match": port}
    return {"hit": False, "severity": "none", "match": None}


def check_goods(description: str) -> dict:
    description_lower = description.lower()
    for keyword in _PROHIBITED_GOODS_KEYWORDS:
        if keyword in description_lower:
            return {"hit": True, "severity": "critical", "match": keyword}
    return {"hit": False, "severity": "none", "match": None}
