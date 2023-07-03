import requests
import cachetools.func
import json
from PIL import Image
from io import BytesIO


from datetime import datetime, timedelta

import datetime as dt
from datetime import datetime

def round_datetime(tm:datetime, delta:int) -> datetime:
    """
    Round down Datatime object to the nearest {delta} mins
    Args:
        tm: datetime object
        delta: nearest mins to round to
    Return:
        Rounded down datetime object
    """

    tm = tm - dt.timedelta(
        minutes=tm.minute % delta,
        seconds=tm.second,
        microseconds=tm.microsecond
    )
    
    return tm


@cachetools.func.ttl_cache(ttl=60)
def get_forecast_24_hour() -> dict:
    """
    Fetch 24 hour forecast from api.

    Returns:
        API response (dict)

    Raises:
        requests.HTTPError: API error
    """

    api_response = requests.get(
        url='https://api.data.gov.sg/v1/environment/24-hour-weather-forecast')
    api_response.raise_for_status()

    api_dict = api_response.json()['items'][0]

    if api_dict == {}:
        raise requests.HTTPError(400, "API Error")
    
    return api_dict 

@cachetools.func.ttl_cache(ttl=60)
def get_forecast_2h() -> dict:
    """
    Fetches 2 hr forecasts from api.

    Returns:
        API response (dict)

    Raises:
        requests.HTTPError: API error
    """

    api_response = requests.get(
        url='https://api.data.gov.sg/v1/environment/2-hour-weather-forecast')
    api_response.raise_for_status()

    api_dict = api_response.json()

    if api_dict["items"][0] == {}:
        raise requests.HTTPError(400, "API Error")

    return api_dict["area_metadata"],api_dict["items"][0]["forecasts"],api_dict["items"][0]


@cachetools.func.ttl_cache(ttl=60)
def get_forecast_4d() -> dict:
    """
    Fetches 4 day forecasts from api.

    Returns:
        API response (dict)

    Raises:
        requests.HTTPError: API error
    """

    api_response = requests.get(
        url='https://api.data.gov.sg/v1/environment/4-day-weather-forecast')
    api_response.raise_for_status()

    api_dict = api_response.json()['items'][0]

    if api_dict == {}:
        raise requests.HTTPError(400, "API Error")
    
    return api_dict 


def get_rainmap(dt: datetime = datetime.now()) -> tuple[datetime, bytes]:
    """
    Fetches rainmaps images from api.

    Returns:
        last updated time and photo (datetime,bytes)

    Raises:
        requests.HTTPError: API error
    """

    return _rainmap_sitch_images(round_datetime(dt, 5))


@cachetools.func.mru_cache()
def _rainmap_static_images():
    static_images_url = [
        "http://www.weather.gov.sg/wp-content/themes/wiptheme/assets/img/base-853.png",
        "http://www.weather.gov.sg/wp-content/themes/wiptheme/images/SG-Township.png",
    ]

    images = []

    for url in static_images_url:
        r = requests.get(url, stream=True)
        r.raise_for_status()

        r.raw.decode_content = True
        images.append(Image.open(r.raw))

    return tuple(images)


def _rainmap__overlay(time: datetime,max_it=5) -> tuple[datetime, Image.Image]:
    time = round_datetime(time, 5)  # round to nearest 5mins

    url = f"http://www.weather.gov.sg/files/rainarea/50km/v2/dpsri_70km_{time.strftime('%Y%m%d%H%M')}0000dBR.dpsri.png"
    r = requests.get(url, stream=True)

    if r.status_code == 200:
        r.raw.decode_content = True
        return time, Image.open(r.raw)

    elif max_it > 0:
        return _rainmap__overlay(time - timedelta(minutes=5),max_it - 1)

    else:
        # Max iterations
        r.status_code = 404  # Force HTTP error to raise
        r.raise_for_status()
        raise requests.HTTPError(404,"API Error")
    
@cachetools.func.ttl_cache(ttl=60)
def _rainmap_sitch_images(time: datetime) -> tuple[datetime, bytes]:
    static_images = _rainmap_static_images()

    rainmap_time, overlay = _rainmap__overlay(time)
    base = static_images[0].convert("RGBA")
    town = static_images[1].resize(base.size).convert("RGBA")
    overlay = overlay.resize(base.size).convert("RGBA")
    overlay.putalpha(70)
    base.paste(overlay, (0, 0), overlay)
    base.paste(town, (0, 0), town)

    photo = BytesIO()
    base.save(photo, 'PNG')
    photo.seek(0)

    return time, photo.read()