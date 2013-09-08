import requests


def get_city_and_address(location):
    """
    returns a tuple like (city, address)
    Arguments:
    - `location`: [lat, lng]
    """
    URL_BASE = "http://maps.googleapis.com/maps/api"
    URL_PATH = URL_BASE + "/geocode/json?latlng=%s,%s&sensor=false" \
        % (location[0], location[1])

    address = ""
    city = ""

    print URL_PATH
    r = requests.get(URL_PATH)
    if r.status_code == 200:
        result = r.json()
        address = result["results"][0]["formatted_address"]
        components = result["results"][0]["address_components"]
        for subdoc in components:
            if "administrative_area_level_1" in subdoc["types"]:
                city = subdoc["long_name"]
                city = city.replace(" Province", "")

        return (address, city)
    else:
        return None

print get_city_and_address([39.978632841102055,
                            32.711729630827904])
