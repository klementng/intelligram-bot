import bot.modules.weather.api.gov_sg as api
import io
import datetime
import difflib

from requests.exceptions import HTTPError
from bot.helper.templates import render_response_template

from telegrambots.wrapper.types.api_method import TelegramBotsMethod
from telegrambots.wrapper.types.methods import *
from telegrambots.wrapper.types.objects import *

from ..base import BaseModule
from bot.core.objects import UserSession


class WeatherModule(BaseModule):
    hook = "/weathersg"
    description = "Get the latest Singapore Weather"

    async def _weather_hook_response(self) -> list[TelegramBotsMethod]:
        """Return message with inline keyboard"""

        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(
                    "Current Rain Map", callback_data=f"{self.hook} rainmap")],
                [InlineKeyboardButton(
                    "2 Hour Nowcast", callback_data=f"{self.hook} forecast2h")],
                [InlineKeyboardButton(
                    "24 Hours Forecast", callback_data=f"{self.hook} forecast24h")],
                [InlineKeyboardButton(
                    "4 Day Outlook", callback_data=f"{self.hook} forecast4d")],
                [InlineKeyboardButton(
                    "Help", callback_data=f"{self.hook} help")]
            ]
        )

        return await self._text_response(f"Select an Option", reply_markup)

    async def _weather_help_response(self) -> list[TelegramBotsMethod]:
        """Render help response"""
        text = render_response_template(
            "weather/templates/help.html", hook=self.hook)

        return await self._text_response(text)

    async def _weather_forecast2h_get_location(self):

        # requires addl self.args
        await self.session.async_update_state(self.args, True)

        if self.is_in_group() == True:
            text = "Enter region (e.g bishan):"
            reply_markup = None

        else:
            text = "Enter region (e.g bishan) or send GPS location:"
            reply_markup = ReplyKeyboardMarkup([[KeyboardButton(
                "Send Current Location", request_location=True)]], one_time_keyboard=True)

        return await self._text_response(text, reply_markup)

    async def _weather_forecast2h_response(self) -> list[TelegramBotsMethod]:
        """24 hr forecast reply"""

        assert self.args[1] == "forecast2h"

        chosen_area = " ".join(self.args[2:]).lower() if len(
            self.args) > 2 else None
        loc_obj = self.tg_obj.location if isinstance(
            self.tg_obj, Message) else None

        # verify arguments
        if loc_obj == None and chosen_area == None:
            return await self._weather_forecast2h_get_location()

        if chosen_area != None and "gps=" in chosen_area:
            try:
                gps = str(self.args[2]).removeprefix("gps=").split(",")
                loc_obj = Location(float(gps[1]), float(gps[0]))

            except Exception as e:
                return await self._exception_response(text=f"Invalid GPS Coord\n\n{e}")

        # Fetch API
        try:
            area_list, forecast_list, items = api.get_forecast_2h()

        except HTTPError as e:
            return await self._exception_response(f"API Error\n\n More Info: {e}\n\n")

        lat, long = None, None

        if isinstance(loc_obj, Location):
            lat = loc_obj.latitude
            long = loc_obj.longitude

        elif chosen_area != '':
            for i, area_dict in enumerate(area_list):
                if area_dict["name"].lower() == chosen_area:
                    long = area_dict["label_location"]["longitude"]
                    lat = area_dict["label_location"]["latitude"]
                    break

        # Show the 5 closest regions
        if lat != None and long != None:
            self.args = list(self.args[0:2]) + [f"gps={lat},{long}"]

            selected_index = []
            distance_from_area = []

            for i, area_dict in enumerate(area_list):
                tmp_distance = (area_dict["label_location"]["longitude"] - long)**2 + (
                    area_dict["label_location"]["latitude"] - lat)**2
                distance_from_area.append(tmp_distance**0.5)

            # select the 5 closest to gps location
            selected_index = sorted(
                range(len(distance_from_area)), key=lambda sub: distance_from_area[sub])[:5]

        else:
            await self.session.async_update_state(self.args[0:2], True)

            possible_areas = difflib.get_close_matches(
                chosen_area, [a_dict["name"] for a_dict in area_list], 10, 0.1)
            possible_areas = ["<pre>"+s+"</pre>" for s in possible_areas]
            return await self._text_response(f"\nUnknown region: '{chosen_area}'\n\nDid you mean:\n- "+"\n- ".join(possible_areas) + "\n\nYou may enter again:",args=self.args[0:2])

        # Render output
        text = render_response_template(
            "weather/templates/forecast2h.html",
            title=f"2 Hour Nowcast",
            update_timestamp=items["update_timestamp"],
            forecasts=[forecast_list[i] for i in selected_index]
        )

        if self.session.message_id != None:
            text += f"\nts:{datetime.datetime.now()}"

        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Refresh", callback_data=" ".join(self.args))]])

        return await self._text_response(text, reply_markup)

    async def _weather_forecast24h_response(self) -> list[TelegramBotsMethod]:
        """24 hr forecast reply"""
        self.args = [s.lower() for s in self.args]

        assert self.args[1] == "forecast24h"

        region_list = ("north", "south", "east", "west", "central")

        # Args check
        if len(self.args) == 2:
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(f"North", callback_data=f"{self.hook} forecast24h north")],
                 [
                    InlineKeyboardButton(
                        f"West", callback_data=f"{self.hook} forecast24h west"),
                    InlineKeyboardButton(
                        f"Central", callback_data=f"{self.hook} forecast24h central"),
                    InlineKeyboardButton(
                        f"East", callback_data=f"{self.hook} forecast24h east")
                ],
                    [InlineKeyboardButton(
                     f"South", callback_data=f"{self.hook} forecast24h south")]
                ]
            )

            return await self._text_response(f"Select an Option", reply_markup)

        elif len(self.args) == 3:
            region = self.args[2]

            if region not in region_list:
                return await self._exception_response(
                    text=f"Invalid region: \"{region}\"\n\nExpected options:\n{region_list}",
                )

            try:
                weather_api = api.get_forecast_24_hour()
            except HTTPError as e:
                return await self._exception_response(f"API Error\n\n More Info: {e}\n\n")

            text = render_response_template(
                "weather/templates/forecast24h.html",
                title=f"24 Hour Forecast ({region})",
                weather_api=weather_api,
                region=region
            )

            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Refresh", callback_data=" ".join(self.args))]])

            if self.session.message_id != None:
                text += f"\nts:{datetime.datetime.now()}"

            return await self._text_response(text, reply_markup)

        else:
            return await self._exception_response(f"Too many arguments, expected max of 3, got {len(self.args)}")

    async def _weather_forecast4d_response(self) -> list[TelegramBotsMethod]:

        assert self.args[1] == "forecast4d"

        try:
            weather_api = api.get_forecast_4d()

        except HTTPError as e:
            return await self._exception_response(f"API Error\n\n More Info: {e}\n\n")

        text = render_response_template(
            "weather/templates/forecast4d.html",
            title=f"4 Day Outlook",
            weather_api=weather_api,
        )

        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Refresh", callback_data=" ".join(self.args))]])

        if self.session.message_id != None:
            text += f"\nts:{datetime.datetime.now()}"

        return await self._text_response(text, reply_markup)

    async def _weather_rainmap_response(self) -> list[TelegramBotsMethod]:
        assert self.args[1] == "rainmap"

        try:
            rainmap_time, photo = api.get_rainmap()
        except HTTPError as e:
            return await self._exception_response("API Error, Please try again later")

        caption = f"Updated: {str(rainmap_time)}"

        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Refresh", callback_data=" ".join([self.hook, self.args[1]]))
        ]])

        # check CallbackQuery is under the photo object
        if isinstance(self.tg_obj, CallbackQuery) and self.tg_obj.message.photo != None:
            self.session.message_id = self.session.message_id
            caption += f"\n\nts: {datetime.datetime.now()}"

        else:
            self.session.message_id = None

        return await self._photo_response(photo, "rainmap.png", caption=caption, reply_markup=reply_markup)

    @classmethod
    async def handle_request(cls, **kwargs) -> list[TelegramBotsMethod]:
        """
        Get replies for commands
        """
        args = kwargs['text'].split(" ")

        assert (args[0] == cls.hook)  # Sanity check

        slf = cls(*args, **kwargs)
        await slf.session.async_update_state(args,False)

        if len(args) == 1:
            res = await slf._weather_hook_response()

        else:
            sub_module = '_weather_%s_response' % args[1]

            if hasattr(slf, sub_module):
                res = await getattr(slf, sub_module)()

            else:
                res = await slf._exception_response(f"Invalid arguments: {args[1:]}")
        
        async with slf.client as client:
            for r in res:
                await client(r)

