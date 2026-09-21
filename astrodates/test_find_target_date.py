import pytest
import swisseph as swe
from datetime import datetime, timedelta
from timezone_api import local_to_utc, utc_to_local

from astrodates import TargetDateFinder, body_longitude, julian_day, BODY_IDS
from zoneinfo import ZoneInfo

#
# HELPERS.
#

# Convert a UTC date/time into a Julian day.
def jd(year: int, month: int, day: int, hour: int = 0,
       minute: int = 0, second: int = 0,
) -> float:
   dt: datetime = datetime(year, month, day, hour, minute, second)
   return julian_day(dt)

# Calculate the next degree that reaches or passes the current degree.
# Temp function to help find the expected degree from the inputs.
def helper_calculate_next_degree(starting_degrees: float,
                                 current_degrees: float,
                                 increment_by: float) -> float:
   degree = starting_degrees

   for _ in range(1000):
      degree = (degree + increment_by) % 360

      if (starting_degrees < current_degrees <= degree or
            degree < starting_degrees and current_degrees <= degree):
         return degree

   raise ValueError("Could not calculate next degree")

# Create a TargetDateFinder with the supplied calculation inputs.
def make_finder(start_jd: float, current_jd: float,
                start_longitude: float, increment: float,
                body_name: str = "Sun",
                tz_name: str = "Australia/Melbourne") -> TargetDateFinder:
   return TargetDateFinder(parent=None,
      start_jd=start_jd, start_longitude=start_longitude,
      current_jd=current_jd,
      inc_longitude=increment,
      body_name=body_name, tz_name=tz_name
   )

#
# HELPER TESTS.
#
# Check Julian Date conversion across multiple time zones and dates.
def test_jd() -> None:
   cases = [
      # UTC
      ((2024, 1, 1, 0, 0), "UTC", 2460310.5),
      ((2024, 6, 1, 12, 30), "UTC", 2460463.0208333335),
      ((2026, 9, 20, 0, 0), "UTC", 2461303.5),

      # Melbourne: AEDT (UTC+11)
      ((2024, 1, 1, 0, 0), "Australia/Melbourne", 2460310.0416666665),

      # Melbourne: AEST (UTC+10)
      ((2024, 6, 1, 12, 30), "Australia/Melbourne", 2460462.6041666665),

      # Melbourne: AEST (UTC+10)
      ((2026, 9, 20, 0, 0), "Australia/Melbourne", 2461303.0833333335),
      #DST change to yes: 2461433.86770)
      ((2027, 1, 28, 18, 49, 29), "Australia/Melbourne", 2461433.82603),

      # Moscow: MSK (UTC+3)
      ((2024, 1, 1, 0, 0), "Europe/Moscow", 2460310.375),
      ((2024, 6, 1, 12, 30), "Europe/Moscow", 2460462.8958333335),
      ((2026, 9, 20, 0, 0), "Europe/Moscow", 2461303.375)
   ]

   for date, tz_name, expected in cases:
      result = jd(*date, tz_name=tz_name)
      assert result == pytest.approx(expected, 0.000001)

#
# INITIAL BASIC TESTS.
#

# Check that zero elapsed time still finds the next target.
def test_zero_elapsed_time() -> None:
   start = jd(2024, 1, 1)
   finder = make_finder(start, start, 280.0, 30.0)

   result = finder.find_target_date()

   assert result > start
   assert finder.running_longitude == pytest.approx(310.0, abs=1e-6)

# Check that one normal increment is found.
def test_single_increment() -> None:
   start = jd(2024, 1, 1, 0, 0, 0, UTC)
   current = jd(2024, 1, 23, 0, 0, 0, UTC)
   start_longitude = body_longitude(start, "Sun", "UTC")
   finder = make_finder(start, current, start_longitude, 30.0)

   result = finder.find_target_date()

   assert result > start
   assert finder.running_longitude == pytest.approx(
      start_longitude + 30.0, abs=1e-6
   )

# Check that repeated increments continue until current is passed.
def test_multiple_increments() -> None:
   start = jd(2024, 1, 1, 0, 0, 0, UTC)
   current = jd(2025, 1, 1, 0, 0, 0, UTC)
   start_longitude = body_longitude(start, "Sun", "UTC")
   finder = make_finder(start, current, start_longitude, 30.0)

   result = finder.find_target_date()

   assert result >= current
   assert finder.running_longitude > start_longitude
   assert (finder.running_longitude - start_longitude) % 30.0 == pytest.approx(
      0.0, abs=1e-6
   )

# Check that a 360-degree increment is handled correctly.
def test_360_degree_increment() -> None:
   start = jd(2020, 1, 1, 0, 0, 0, UTC)
   current = jd(2022, 1, 1, 0, 0, 0, UTC)
   start_longitude = body_longitude(start, "Sun", "UTC")
   finder = make_finder(start, current, start_longitude, 360.0)

   result = finder.find_target_date()

   assert result > start
   assert finder.running_longitude == pytest.approx(
      start_longitude + 720.0, abs=1e-6
   )

# Check that crossing 360 degrees does not lose the progression.
def test_longitude_wraparound() -> None:
   start = jd(2024, 1, 1)
   current = jd(2024, 3, 1)
   finder = make_finder(start, current, 359.0, 2.0)

   result = finder.find_target_date()

   assert result > start
   assert finder.running_longitude == pytest.approx(361.0, abs=1e-6)

# Check that long elapsed periods use the revolution calculation.
def test_multiple_revolutions() -> None:
   start = jd(2000, 1, 1, 0, 0, 0, UTC)
   current = jd(2025, 1, 1, 0, 0, 0, UTC)
   start_longitude = body_longitude(start, "Sun", "UTC")
   finder = make_finder(start, current, start_longitude, 30.0)

   finder.show_log = lambda: None
   result = finder.find_target_date()

   assert result >= current
   assert finder.revolutions > 0
   assert finder.running_longitude > start_longitude

# Check that a very small increment is repeatedly applied.
def test_small_increment() -> None:
   start = jd(2024, 1, 1, 0, 0, 0, UTC)
   current = jd(2024, 1, 10, 0, 0, 0, UTC)
   start_longitude = body_longitude(start, "Sun", "UTC")
   finder = make_finder(start, current, start_longitude, 0.001)

   result = finder.find_target_date()

   assert result >= current
   assert finder.running_longitude > start_longitude
   assert finder.running_longitude - start_longitude > 0.001
   assert finder.running_longitude > start_longitude + 0.001

#
# Tests: Sun/Moon/MC
# Fixed values independently obtained from Swiss Ephemeris.
#

# Check Sun targets against fixed external ephemeris values.
def test_ephemeris_sun_targets() -> None:
   cases = [
      # Test case layout:
      # (
      #  (start date), start_longitude, timezone,
      #  (current_date), degree_increment,
      #  (expected target date), (expected_target_julian)
      # )
      (
         # longitude = sign_start + degrees + minutes / 60
         # 8Vir11'25" = 158.1903340
         (2026, 9, 1, 0, 0, 0), 158.1903340, "Australia/Melbourne",
         (2026, 9, 1, 0, 0, 0), 30,
         # Expected after 30 degrees:
         # 8Lib11'25" = 188.1903340 -> julian: 2461314.85774
         (2026, 10, 1, 18, 35, 8), 2461314.85774
      ),
      (
         # This is the first test we did that tests a dst transition.
         # 8Vir11'25" = 158.1903340
         (2026, 9, 1, 0, 0, 0), 158.1903340, "Australia/Melbourne",
         (2026, 9, 17, 0, 0, 0), 150,
         # Expected: 8Aqu11'25 = 308.1903340 -> julian: 2461433.86770
         (2027, 1, 28, 19, 49, 29), 2461433.86770
      ),
      (
         # This is the first test we will introduce a bunch of revolutions.
         (1971, 1, 1, 0, 0, 0), 279.4887547, "UTC",
         # Current degrees: 173.7294410
         (2026, 9, 17, 0, 0, 0), 30,
         # Expected: 189.4887547 -> julian: 2461316.17818
         (2026, 10, 2, 16, 16, 34), 2461316.17818
      ),
      (
         # This is the first test we will introduce a bunch of revolutions.
         (1971, 1, 1, 0, 0, 0), 279.4887547, "UTC",
         # Current degrees: 173.7294410
         (2026, 9, 17, 0, 0, 0), 45,
         # Expected: 189.4887547 -> julian: 2461316.17818
         (2026, 10, 2, 16, 16, 34), 2461316.17818
      )
   ]

   for (
      start_date, start_longitude, time_zone,
      current_date, inc_longitude,
      expected_date, expected_julian
   ) in cases:
      # Convert local input times to UTC.
      start_utc: datetime = local_to_utc(
         datetime(*start_date), time_zone
      )
      current_utc: datetime = local_to_utc(
         datetime(*current_date), time_zone
      )

      # Convert UTC times to Julian days.
      start_jd: float = julian_day(start_utc)
      current_jd: float = julian_day(current_utc)

      # Find the target using UTC Julian days.
      finder: TargetDateFinder = make_finder(
         start_jd, current_jd, start_longitude, inc_longitude
      )
      result_jd: float = finder.find_target_date()

      # Convert the result JD to a UTC datetime.
      year, month, day, hour = swe.revjul(result_jd, swe.GREG_CAL)
      result_utc: datetime = datetime(year, month, day) + timedelta(hours=hour)

      # Convert the UTC result to local time.
      result_local: datetime = utc_to_local(
         result_utc, time_zone
      ).replace(tzinfo=None)

      # Calculate the JD from the resulting local clock time.
      result_julian: float = julian_day(result_local)
      expected_local: datetime = datetime(*expected_date)

      assert result_julian == pytest.approx(
         expected_julian, 0.000001
      )
      assert abs(result_local - expected_local) <= timedelta(seconds=1)
