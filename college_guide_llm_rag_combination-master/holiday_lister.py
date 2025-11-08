import requests
import json
import datetime
# --- Configuration ---
# Replace with your actual API key from Calendarific
API_KEY = 'TJWAAyFHif4KQWeaSUOojGRwedxDWtOn'
COUNTRY_CODE = 'IN'  # Use ISO 3166-1 alpha-2 country codes
YEAR = datetime.datetime.now().year

# Construct the API URL
url = f"https://calendarific.com/api/v2/holidays?api_key={API_KEY}&country={COUNTRY_CODE}&year={YEAR}"

# --- API Request and Processing ---

def get_holiday_list():
    try:
        # Check if the API key has been set
        if API_KEY == 'YOUR_API_KEY_HERE':
            print("\nError: Please replace 'YOUR_API_KEY_HERE' with your actual API key.")
        else:
            response = requests.get(url, timeout=15)

            # Check for HTTP errors (e.g., 401 Unauthorized, 404 Not Found)
            response.raise_for_status()

            # The API response is nested under a 'response' -> 'holidays' structure
            data = response.json()
            holidays_list = data.get('response', {}).get('holidays', [])

            #print(holidays_list)

            if holidays_list:
                return holidays_list
            else:
                return []
                print("No holidays found for the specified country and year.")

    except requests.exceptions.HTTPError as e:
        # Handle specific HTTP status code errors
        if e.response.status_code == 401:
            print("\nHTTP Error 401: Unauthorized. Please check if your API key is correct and valid.")
        else:
            print(f"\nHTTP Error occurred: {e}")
    except requests.exceptions.RequestException as e:
        # Handle network-related errors
        print(f"\nNetwork request failed: {e}")
    except json.JSONDecodeError:
        print("Failed to decode JSON from the response. The API might be down or returning an error page.")
