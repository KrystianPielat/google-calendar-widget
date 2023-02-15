from __future__ import print_function

import datetime
import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# from googleapiclient.errors import HttpError
# from httplib2.error import ServerNotFoundError


class CalendarHandler:
    def __init__(self) -> None:
        self.creds = self.auth()
        self.service = build("calendar", "v3", credentials=self.creds)
        self.now = datetime.datetime.now()
        self.tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)

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
            return creds
        except:
            print("failed to authenticate")
            return None

    def get_calendars(self):
        try:
            return [
                cal["id"]
                for cal in self.service.calendarList().list().execute().get("items", [])
            ]
        except:
            print("Error getting calendars")

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
        except:
            print("Failed to retrieve events for calendar: ", cal_id)
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
                event["start"]["dateTime"], "%Y-%m-%dT%H:%M:%S+01:00"
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
        events = []
        for cal_id in calendars:
            cal_events = self.get_events_for_calendar(cal_id)
            if cal_events:
                events.extend(cal_events)

        return events

        # except HttpError:
        # print("Error")
        # except ServerNotFoundError:
        # return

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
    event = handler.get_closest_event()
    if event:
        print(CalendarHandler.format_event(event))
        return
    print("")
    return

if __name__ == "__main__":
    main()
