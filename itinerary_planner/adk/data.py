# Mock Data for Itinerary Planner
FLIGHT_DATA = [
    {"id": "F1", "airline": "Japan Airlines", "departure": "2026-05-01T08:00", "arrival": "2026-05-01T20:00", "price": 450, "origin": "SFO", "destination": "HND"},
    {"id": "F2", "airline": "United", "departure": "2026-05-01T10:00", "arrival": "2026-05-01T22:00", "price": 500, "origin": "SFO", "destination": "NRT"},
    {"id": "F3", "return_id": "F3R", "airline": "Japan Airlines", "departure": "2026-05-04T18:00", "arrival": "2026-05-04T10:00", "price": 400, "origin": "HND", "destination": "SFO"}
]

HOTEL_DATA = [
    {"id": "H1", "name": "Hotel Sunroute Plaza Shinjuku", "price_per_night": 120, "location": "Shinjuku", "available": True},
    {"id": "H2", "name": "Park Hyatt Tokyo", "price_per_night": 600, "location": "Shinjuku", "available": True},
    {"id": "H3", "name": "Apa Hotel", "price_per_night": 80, "location": "Shibuya", "available": True}
]

ATTRACTION_DATA = [
    {"name": "TeamLab Borderless", "fee": 30},
    {"name": "Tokyo Skytree", "fee": 25},
    {"name": "Ghibli Museum", "fee": 10},
    {"name": "Meiji Jingu Shrine", "fee": 0}
]
