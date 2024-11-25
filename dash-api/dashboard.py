import hashlib
import json
from io import BytesIO
import itertools
import json
from datetime import datetime


from dataclasses import asdict, dataclass, is_dataclass
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from .leaf import LeafData, get_leaf_data
from .messages import get_message
from .stocks import StockData, get_stock_data
from .temperature import TemperatureData, get_all_temperature_data
from .weather import WeatherData, get_rounded_weather_data, get_weather_data


def hash_data(data):
    if is_dataclass(data):
        data = asdict(data)
    data_string = json.dumps(data)
    data_hash = hash(data_string)
    return data_hash

@dataclass
class Action:
    id: str
    display_text: str

@dataclass
class DashboardData:
    leaf: LeafData
    date_string: str
    message: str
    weather: WeatherData | None
    # stocks: list[StockData]
    pistat0: TemperatureData
    actions: list[Action] = None


def get_dashboard_data():
    leaf_data = get_leaf_data()
    # stock_data = get_stock_data()

    pistat0 = get_all_temperature_data().get("pistat-0", None)
    if pistat0:
        pistat0.temperature = round(pistat0.temperature, 1)
        pistat0.humidity = round(pistat0.humidity, 1)

    weather = get_weather_data()
    if weather:
        # take up to three weather forecast entries
        forecast = list(itertools.islice(weather.forecast, 2))
        forecast = [get_rounded_weather_data(w) for w in forecast]
        current = get_rounded_weather_data(weather.current)
        weather = WeatherData(current=current, forecast=forecast)

    dashboard_data = DashboardData(
        leaf=leaf_data,
        date_string=datetime.now().strftime("%A, %d %B %Y"),
        message=get_message(datetime.now().date()),
        weather=weather,
        # stocks=stock_data,
        pistat0=pistat0,
        actions=[
            Action(id="refresh", display_text="Refresh"),
        ]
    )

    return dashboard_data


def yes_no(value: bool):
    return "Yes" if value else "No"


def pure_pil_alpha_to_color_v2(image, color=(255, 255, 255)):
    """Alpha composite an RGBA Image with a specified color.

    Simpler, faster version than the solutions above.

    Source: http://stackoverflow.com/a/9459208/284318

    Keyword Arguments:
    image -- PIL RGBA Image object
    color -- Tuple r, g, b (default 255, 255, 255)

    """
    # from: https://stackoverflow.com/questions/9166400/convert-rgba-png-to-rgb-with-pil
    image.load()  # needed for split()
    background = Image.new("RGB", image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background


def get_image_hash(image_buf):
    hash_md5 = hashlib.md5()
    hash_md5.update(image_buf.getvalue())
    image_hash = hash_md5.hexdigest()
    return image_hash


def generate_dashboard_image(dashboard_data: DashboardData):
    image = Image.new(mode="RGBA", size=(800, 480), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    message_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 25)

    draw_heading(image, draw, dashboard_data)

    draw_leaf_info(image, draw, dashboard_data.leaf)

    draw_weather(image, draw, dashboard_data.weather,
                 weather_left=30, weather_top=140)
    
    if dashboard_data.pistat0 is not None:
        temp_top = 340
        temp_left = 30
        temp_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)
        draw.text(
            (temp_left, temp_top),
            f"pistat-0: {dashboard_data.pistat0.temperature}°C ({dashboard_data.pistat0.humidity}%)",
            fill=(0, 0, 0),
            font=temp_font,
        )

    # stock_left = 30
    # stock_top = 340

    # stock_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)
    # top = stock_top
    # left = stock_left
    # for stock in dashboard_data.stocks:
    #     draw.text(
    #         (left, top),
    #         f"{stock.symbol}: {stock.price} {stock.currency}",
    #         fill=(0, 0, 0),
    #         font=stock_font,
    #     )
    #     left += 250

    # draw lines and text for buttons
    action_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 15)
    for i, x in enumerate([80, 240, 400, 560, 720]):
        draw.line((x, 460, x, 490), fill=(0, 0, 0))
        if dashboard_data.actions and len(dashboard_data.actions) > i:
            action = dashboard_data.actions[i]
            draw_centred(
                draw,
                (x + 5, 440),
                action.display_text,
                font=action_font,
            )

    message_font_size = 25
    message = dashboard_data.message
    while message_font_size > 10:
        message_font = ImageFont.truetype(
            "fonts/FiraCode-Regular.ttf", message_font_size
        )
        message_width = draw.textlength(message, font=message_font)
        if message_width < image.width - 20:
            message_x = (image.width - message_width) / 2
            draw.text((message_x, 400), message,
                      fill=(0, 0, 0), font=message_font)
            break
        message_font_size -= 1

    # handle the alpha channel (needed for PNGs from OpenWeatherMap)
    image = pure_pil_alpha_to_color_v2(image)

    image_buf = BytesIO()
    image.save(image_buf, "JPEG")
    image_buf.seek(0)
    return image_buf


def draw_centred(draw, xy, text, font):
    """Draw text centred on the x coordinate.
    Returns the width of the text drawn."""
    x = xy[0]
    y = xy[1]
    text_width = draw.textlength(text, font=font)
    text_x = x - (text_width) / 2
    draw.text((text_x, y), text, fill=(0, 0, 0), font=font)
    return text_width


def draw_weather(image, draw, weather, weather_left, weather_top):
    weather_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)
    weather_font_temp_main = ImageFont.truetype(
        "fonts/FiraCode-Regular.ttf", 30)
    weather_font_temp_feels_like = ImageFont.truetype(
        "fonts/FiraCode-Regular.ttf", 20)
    weather_font_description = ImageFont.truetype(
        "fonts/FiraCode-Regular.ttf", 15)
    weather_width = 200

    if weather:
        weather_list = [weather.current] + weather.forecast
        for idx, weather in enumerate(weather_list):
            # load weather icon
            weather_icon = Image.open(weather.icon_path)

            # darken the image as light clouds etc are hard to see on the eink display
            enhancer = ImageEnhance.Brightness(weather_icon)
            weather_icon = enhancer.enhance(0.65)

            if idx == 0:
                weather_icon = weather_icon.resize((150, 150))
                weather_font = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 20)
                weather_font_temp_main = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 30
                )
                weather_font_temp_feels_like = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 20
                )
                weather_font_description = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 20
                )
                weather_width = 250
                weather_x_offset = 50
                temp_offset = 35
                feels_like_offset = 35
                description_offset = 60
                wind_offset = 25
            else:
                weather_icon = weather_icon.resize((85, 85))
                weather_font = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 17)
                weather_font_temp_main = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 25
                )
                weather_font_temp_feels_like = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 15
                )
                weather_font_description = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 15
                )
                weather_x_offset = 10
                weather_width = 200
                temp_offset = 25
                feels_like_offset = 35
                description_offset = 30
                wind_offset = 15

            current_y = weather_top
            image.paste(weather_icon, box=(weather_left, current_y + 5))
            draw_centred(
                draw,
                (weather_left + (weather_width / 2), current_y),
                weather.time,
                font=weather_font,
            )

            current_y += temp_offset
            draw.text(
                (weather_left + weather_icon.width, current_y),
                f"{weather.temperature:.0f}°C",
                fill=(0, 0, 0),
                font=weather_font_temp_main,
            )

            current_y += feels_like_offset
            draw.text(
                (weather_left + weather_icon.width, current_y),
                f"({weather.feels_like:.0f}°C)",
                fill=(0, 0, 0),
                font=weather_font_temp_feels_like,
            )

            current_y += description_offset
            draw_centred(
                draw,
                (weather_left + weather_width / 2, current_y),
                weather.description,
                font=weather_font_description,
            )

            current_y += wind_offset
            wind_speed_text = f"{weather.wind_speed_mph:.0f}" if weather.wind_speed_mph else "n/a"
            wind_gust_text = f"{weather.wind_gust_mph:.0f}" if weather.wind_gust_mph else "n/a"
            draw_centred(
                draw,
                (weather_left + weather_width / 2, current_y),
                f"{wind_speed_text} mph ({wind_gust_text} mph gusts)",
                font=weather_font_description,
            )
            weather_left += weather_width + weather_x_offset


def draw_leaf_info(image: Image, image_draw: ImageDraw, leaf_info: LeafData):
    info_main_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 35)
    info_sub_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)

    cruising_range_ac_off_miles = leaf_info.cruising_range_ac_off_miles
    cruising_range_ac_on_miles = leaf_info.cruising_range_ac_on_miles

    image_draw.text(
        (110, 50),
        f"Range: {cruising_range_ac_off_miles:.0f} miles",
        fill=(0, 0, 0),
        font=info_main_font,
    )
    image_draw.text(
        (110, 90),
        f"({cruising_range_ac_on_miles:.0f} with climate control)",
        fill=(0, 0, 0),
        font=info_sub_font,
    )
    leaf_image = Image.open(leaf_info.icon_path)
    image.paste(leaf_image, box=(10, 40))


def draw_heading(image: Image, draw: ImageDraw, dashboard_data):
    heading_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 25)

    title = "Leeks Dashboard"
    title_width = draw.textlength(title, font=heading_font)
    title_x = (image.width / 2 - title_width) / 2
    draw.text((title_x, 10), title, fill=(0, 0, 0), font=heading_font)

    date_text = dashboard_data.date_string
    date_width = draw.textlength(date_text, font=heading_font)
    date_x = image.width - date_width - 10
    draw.text((date_x, 10), date_text, fill=(0, 0, 0), font=heading_font)
