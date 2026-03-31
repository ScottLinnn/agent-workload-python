import sys
import json
import os
# Absolute path to the root of the repo (relative to this file)
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(ROOT_PATH)

from itinerary_planner.adk.data import FLIGHT_DATA, HOTEL_DATA, ATTRACTION_DATA

def evaluate():
    itinerary_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    json_path = os.path.join(itinerary_dir, 'itinerary.json')
    if not os.path.exists(json_path):
        print(f"FAILED: {json_path} does not exist.")
        return False
        
    with open(json_path, 'r') as f:
        try:
            itinerary = json.load(f)
        except json.JSONDecodeError:
            print("FAILED: itinerary.json is not valid JSON.")
            return False
            
    # Factual check against data.py
    # 1. Flight prices
    actual_flight_cost = 0
    # Robust key check
    itinerary_flights = itinerary.get('flights') or itinerary.get('flight_details', {})
    outbound = itinerary_flights.get('outbound', {})
    return_flight = itinerary_flights.get('return', {})
    
    # helper to find factual flight price
    def find_flight_price(flight_info):
        flight_id = flight_info.get('id')
        if flight_id:
            for f in FLIGHT_DATA:
                if f['id'] == flight_id:
                    return f['price']
        # Fallback to name/airline/departure match if ID is missing
        airline = flight_info.get('airline')
        departure = flight_info.get('departure')
        for f in FLIGHT_DATA:
            if f.get('airline') == airline and f.get('departure') == departure:
                return f['price']
        return None

    outbound_price = find_flight_price(outbound)
    return_price = find_flight_price(return_flight)
    
    if outbound_price is None or return_price is None:
        print(f"FAILED: Factual flight data not found for outbound {outbound} or return {return_flight}")
        return False
    
    actual_flight_cost = outbound_price + return_price
    
    # 2. Hotel price
    actual_hotel_cost = 0
    hotel_info = itinerary.get('hotel') or itinerary.get('hotel_details', {})
    hotel_id = hotel_info.get('id')
    hotel_name = hotel_info.get('name')
    factual_hotel = None
    
    if hotel_id:
        for h in HOTEL_DATA:
            if h['id'] == hotel_id:
                factual_hotel = h
                break
    
    if factual_hotel is None and hotel_name:
        for h in HOTEL_DATA:
            if h['name'] == hotel_name:
                factual_hotel = h
                break
    
    if factual_hotel is None:
        print(f"FAILED: Factual hotel data not found for {hotel_name} (ID: {hotel_id})")
        return False
        
    num_nights = hotel_info.get('number_of_nights')
    if num_nights is None:
        # try to infer from total_hotel_cost if available
        reported_hotel_cost = hotel_info.get('total_hotel_cost')
        if reported_hotel_cost:
            num_nights = reported_hotel_cost / factual_hotel['price_per_night']
        else:
            num_nights = 3 # default to 3 as per instructions
            
    actual_hotel_cost = factual_hotel['price_per_night'] * num_nights
    
    # 3. Attraction fees
    actual_attraction_cost = 0
    itinerary_attractions = itinerary.get('attractions', [])
    for it_attr in itinerary_attractions:
        factual_attr = None
        for a in ATTRACTION_DATA:
            if a['name'] == it_attr.get('name'):
                factual_attr = a
                break
        if factual_attr is None:
            print(f"FAILED: Factual attraction data not found for {it_attr.get('name')}")
            return False
        actual_attraction_cost += factual_attr['fee']
        
    total_factual_cost = actual_flight_cost + actual_hotel_cost + actual_attraction_cost
    
    if total_factual_cost > 1200:
        print(f"FAILED: Factual total cost {total_factual_cost} exceeds $1200.")
        return False
        
    print(f"PASSED: Factual total cost is {total_factual_cost} (<= $1200).")
        
    print("PASSED: Itinerary Planner evaluation successful.")
    return True

if __name__ == "__main__":
    if evaluate():
        sys.exit(0)
    else:
        sys.exit(1)
