from __future__ import annotations

GENDER_NAMES: dict[str, list[str]] = {
    "woman": [
        "Emma",
        "Olivia",
        "Sophie",
        "Hannah",
        "Chloe",
        "Grace",
        "Laura",
        "Rachel",
        "Alice",
        "Emily",
    ],
    "man": [
        "James",
        "Oliver",
        "William",
        "Thomas",
        "Daniel",
        "Michael",
        "David",
        "Andrew",
        "Robert",
        "Peter",
    ],
}

ORIGIN_NAMES: dict[str, list[tuple[str, str]]] = {
    "anglo": [
        ("James", "Whitfield"),
        ("Oliver", "Hartley"),
        ("Thomas", "Bramley"),
        ("Daniel", "Ashford"),
        ("Andrew", "Kendrick"),
        ("Peter", "Lockhart"),
    ],
    "african": [
        ("Kwame", "Mensah"),
        ("Chidi", "Okafor"),
        ("Tunde", "Adeyemi"),
        ("Sipho", "Dlamini"),
        ("Kofi", "Boateng"),
        ("Emeka", "Nwosu"),
    ],
    "east_asian": [
        ("Wei", "Chen"),
        ("Jun", "Nakamura"),
        ("Ming", "Zhao"),
        ("Haruto", "Sato"),
        ("Jin", "Park"),
        ("Cheng", "Liu"),
    ],
    "south_asian": [
        ("Arjun", "Patel"),
        ("Rohan", "Sharma"),
        ("Vikram", "Iyer"),
        ("Aditya", "Rao"),
        ("Nikhil", "Mehta"),
        ("Sanjay", "Kulkarni"),
    ],
    "middle_eastern": [
        ("Omar", "Haddad"),
        ("Yusuf", "Khalil"),
        ("Karim", "Nasser"),
        ("Tariq", "Mansour"),
        ("Sami", "Farouk"),
        ("Rami", "Saleh"),
    ],
}

NEUTRAL_FIRST_NAMES = [
    "Jordan",
    "Casey",
    "Morgan",
    "Riley",
    "Avery",
    "Quinn",
    "Rowan",
    "Taylor",
    "Elliot",
    "Sasha",
]

NEUTRAL_SURNAMES = [
    "Bennett",
    "Hughes",
    "Sullivan",
    "Reed",
    "Coleman",
    "Foster",
    "Hayes",
    "Barker",
    "Newton",
    "Parker",
]

ATTRIBUTE_LABELS: dict[str, dict[str, str]] = {
    "gender": {
        "woman": "Woman-coded name",
        "man": "Man-coded name",
    },
    "name_origin": {
        "anglo": "Anglo",
        "african": "African",
        "east_asian": "East Asian",
        "south_asian": "South Asian",
        "middle_eastern": "Middle Eastern",
    },
    "age": {
        "early_career": "Early career",
        "mid_career": "Mid career",
        "senior": "Senior",
    },
}

ATTRIBUTE_ORDER = ["gender", "name_origin", "age"]
ORIGIN_GROUPS = ["anglo", "african", "east_asian", "south_asian", "middle_eastern"]
AGE_GROUPS = ["early_career", "mid_career", "senior"]
GENDER_GROUPS = ["woman", "man"]


def all_known_first_names() -> set[str]:
    names = {name.lower() for names in GENDER_NAMES.values() for name in names}
    names.update(first.lower() for group in ORIGIN_NAMES.values() for first, _ in group)
    names.update(name.lower() for name in NEUTRAL_FIRST_NAMES)
    return names


def all_known_surnames() -> set[str]:
    names = {surname.lower() for value in ORIGIN_NAMES.values() for _, surname in value}
    names.update(surname.lower() for surname in NEUTRAL_SURNAMES)
    return names
