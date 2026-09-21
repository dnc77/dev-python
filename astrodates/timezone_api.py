from datetime import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


COMMON_TIMEZONES = [
   "UTC",
   "Australia/Melbourne",
   "Australia/Sydney",
   "Australia/Brisbane",
   "Australia/Adelaide",
   "Australia/Perth",
   "Pacific/Auckland",
   "Asia/Tokyo",
   "Asia/Seoul",
   "Asia/Shanghai",
   "Asia/Singapore",
   "Asia/Hong_Kong",
   "Asia/Bangkok",
   "Asia/Kolkata",
   "Asia/Dubai",
   "Europe/London",
   "Europe/Paris",
   "Europe/Berlin",
   "Europe/Rome",
   "Europe/Madrid",
   "Europe/Moscow",
   "Europe/Athens",
   "Europe/Istanbul",
   "Africa/Cairo",
   "Africa/Johannesburg",
   "America/New_York",
   "America/Chicago",
   "America/Denver",
   "America/Los_Angeles",
   "America/Toronto",
   "America/Vancouver",
   "America/Mexico_City",
   "America/Sao_Paulo",
   "America/Argentina/Buenos_Aires",
]


TIMEZONE_COORDINATES = {
   "UTC": (0.0, 0.0),
   "Australia/Melbourne": (-37.8167, 144.9667),
   "Australia/Sydney": (-33.8667, 151.2000),
   "Australia/Brisbane": (-27.4667, 153.0333),
   "Australia/Adelaide": (-34.9333, 138.6000),
   "Australia/Perth": (-31.9500, 115.8667),
   "Pacific/Auckland": (-36.8500, 174.7667),
   "Asia/Tokyo": (35.6833, 139.6833),
   "Asia/Seoul": (37.5667, 126.9833),
   "Asia/Shanghai": (31.2333, 121.4667),
   "Asia/Singapore": (1.2833, 103.8500),
   "Asia/Hong_Kong": (22.2833, 114.1500),
   "Asia/Bangkok": (13.7500, 100.5167),
   "Asia/Kolkata": (22.5667, 88.3500),
   "Asia/Dubai": (25.2500, 55.3000),
   "Europe/London": (51.5000, -0.1167),
   "Europe/Paris": (48.8500, 2.3500),
   "Europe/Berlin": (52.5167, 13.4000),
   "Europe/Rome": (41.9000, 12.4833),
   "Europe/Madrid": (40.4000, -3.6833),
   "Europe/Moscow": (55.7500, 37.6167),
   "Europe/Athens": (37.9833, 23.7333),
   "Europe/Istanbul": (41.0167, 28.9667),
   "Africa/Cairo": (30.0500, 31.2500),
   "Africa/Johannesburg": (-26.2000, 28.0500),
   "America/New_York": (40.7167, -74.0000),
   "America/Chicago": (41.8833, -87.6333),
   "America/Denver": (39.7500, -104.9833),
   "America/Los_Angeles": (34.0500, -118.2500),
   "America/Toronto": (43.6667, -79.4167),
   "America/Vancouver": (49.2667, -123.1167),
   "America/Mexico_City": (19.4333, -99.1333),
   "America/Sao_Paulo": (-23.5500, -46.6333),
   "America/Argentina/Buenos_Aires": (
      -34.6000,
      -58.3833,
   ),
}


def local_to_utc(local_dt, tz_name):
   """Convert a local datetime to UTC using the selected IANA timezone."""
   try:
      zone = ZoneInfo(tz_name)
   except ZoneInfoNotFoundError:
      raise ValueError("The selected timezone is not available.")

   local_0 = local_dt.replace(tzinfo=zone, fold=0)
   local_1 = local_dt.replace(tzinfo=zone, fold=1)

   utc_0 = local_0.astimezone(timezone.utc)
   utc_1 = local_1.astimezone(timezone.utc)

   back_0 = utc_0.astimezone(zone).replace(tzinfo=None)
   back_1 = utc_1.astimezone(zone).replace(tzinfo=None)

   valid_0 = back_0 == local_dt
   valid_1 = back_1 == local_dt

   if not valid_0 and not valid_1:
      raise ValueError(
         "The selected local time does not exist because of a "
         "daylight-saving transition."
      )

   if valid_0:
      return utc_0.replace(tzinfo=None)

   return utc_1.replace(tzinfo=None)


def utc_to_local(utc_dt, tz_name):
   """Convert a UTC datetime to the selected local timezone."""
   try:
      zone = ZoneInfo(tz_name)
   except ZoneInfoNotFoundError:
      raise ValueError("The selected timezone is not available.")

   aware = utc_dt.replace(tzinfo=timezone.utc)
   return aware.astimezone(zone)


def timezone_coordinates(tz_name):
   try:
      return TIMEZONE_COORDINATES[tz_name]
   except KeyError:
      raise ValueError(
         "Geographic coordinates are not stored for the selected "
         "timezone. Please select one of the supported timezones."
      )
