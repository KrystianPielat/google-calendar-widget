from __future__ import print_function

import datetime
import os.path
import logging
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# from googleapiclient.errors import HttpError
# from httplib2.error import ServerNotFoundError


class CalendarHandler:
    def __init__(self) -> None:
        self.logger = self._logger_init()
        # tz = pytz.timezone('Europe/Madrid')
        self.now = datetime.datetime.now() # TODO Timedelta bcs i didnt set the timezone correctly
        self.tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        self.logger.info("Running.")

    def _logger_init(self):
        logger = logging.getLogger()
        # logger.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s", "%m-%d-%Y %H:%M:%S"
        )

        # stdout_handler = logging.StreamHandler(sys.stdout)
        # stdout_handler.setLevel(logging.INFO)
        # stdout_handler.setFormatter(formatter)

        fh_err = logging.FileHandler("logs.log")
        fh_err.setLevel(logging.ERROR)
        fh_err.setFormatter(formatter)

        fh_info = logging.FileHandler("logs.log")
        fh_info.setLevel(logging.INFO)
        fh_info.setFormatter(formatter)

        logger.addHandler(fh_info)
        logger.addHandler(fh_err)

        return logger

    def auth(self):
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        try:
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        "credentials.json", SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open("token.json", "w") as token:
                    token.write(creds.to_json())

            self.creds = creds
            self.service = build("calendar", "v3", credentials=self.creds)

            return True
        except Exception as e:
            self.logger.error("Authentication: " + str(e))
            return False

    def get_calendars(self):
        try:
            return [
                cal["id"]
                for cal in self.service.calendarList().list().execute().get("items", [])
            ]
        except Exception as e:
            self.logger.error("get_calendars: " + str(e))
            return None

    def get_events_for_calendar(self, cal_id):
        try:
            events_res = (
                self.service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=self.now.isoformat() + "Z",
                    timeMax=self.tomorrow.isoformat() + "Z",
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except Exception as e:
            self.logger.error(
                "get_events_for_calendar, cal_id = {}: {}".format(cal_id, str(e))
            )
        if not events_res.get("items", []):
            return None
        cal_events = [
            event_res
            for event_res in events_res.get("items", [])
            if "dateTime" in event_res["start"]
        ]
        output = []
        for event in cal_events:
            time = datetime.datetime.strptime(
                event["start"]["dateTime"], "%Y-%m-%dT%H:%M:%S+02:00"
            )
            if time < self.now:
                continue
            summary = (
                (event["summary"][:10] + "..")
                if len(event["summary"]) > 10
                else event["summary"]
            )
            output.append((summary, time))
        return output

    def get_all_events(self):
        calendars = self.get_calendars()
        if not calendars:
            return None
        events = []
        for cal_id in calendars:
            cal_events = self.get_events_for_calendar(cal_id)
            if cal_events:
                events.extend(cal_events)

        return events

    def get_closest_event(self):
        events = self.get_all_events()
        if not events:
            return None
        return sorted(events, key=lambda x: x[1])[0]

    @staticmethod
    def format_event(event):
        return "{} {}".format(event[0], event[1].strftime("%H:%M"))


def main():

    handler = CalendarHandler()
    try:
        handler.auth()
        event = handler.get_closest_event()
        if event:
            print(CalendarHandler.format_event(event))
            return
        print("None")
        return
    except Exception as e:
        handler.logger.error(str(e))
        print("Err")


if __name__ == "__main__":
    main()
