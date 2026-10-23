
locations = [
    {"id": "gate", "name": "Main Gate"},
    {"id": "library", "name": "Central Library"},
    {"id": "blockA", "name": "Academic Block A"},
    {"id": "cafeteria", "name": "Cafeteria"},
    {"id": "hostel", "name": "Student Hostel"},
    {"id": "sports", "name": "Sports Complex"},
]

edges = [
    ("gate", "library", 120),
    ("gate", "cafeteria", 150),
    ("library", "blockA", 130),
    ("library", "cafeteria", 180),
    ("cafeteria", "hostel", 140),
    ("blockA", "hostel", 200),
    ("blockA", "sports", 160),
    ("hostel", "sports", 170),
]
