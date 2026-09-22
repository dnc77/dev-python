import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta, timezone

import swisseph as swe
from tkcalendar import DateEntry

from timezone_api import (
   COMMON_TIMEZONES,
   local_to_utc,
   utc_to_local,
   timezone_coordinates
)

VERSION: str = "1.00.0002a (github edition - prototype)"
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

#
# Astronomical body and angular-point definitions.
# The displayed text includes the approximate full zodiac cycle.
#

BODY_OPTIONS = {
   "Sun — (360° = ~365.24 days)": "Sun",
   "Moon — (360° = ~27.3 days)": "Moon",
   "MC — (360° = ~24 hours)": "MC"
}

BODY_IDS = {
   "Sun": swe.SUN,
   "Moon": swe.MOON
}

#
# Revolution bounds.
# Used for coarse revolution calculations.
#
MIN_DAYS_BODY_REVOLUTION = {
   "Sun": 353.0,
   "Moon": 23.0,
   "MC": 0.9972695664
}
MAX_DAYS_BODY_REVOLUTION = {
   "Sun": 366.0,
   "Moon": 28.0,
   "MC": 0.9972695664
}

ZODIAC_SIGNS = (
   "Aries",
   "Taurus",
   "Gemini",
   "Cancer",
   "Leo",
   "Virgo",
   "Libra",
   "Scorpio",
   "Sagittarius",
   "Capricorn",
   "Aquarius",
   "Pisces"
)


#
# Julian day calculation.
# Swiss Ephemeris calculations are performed using UTC.
#

# Convert a naive UTC datetime to a Julian day.
def julian_day(dt):
   """Convert a naive UTC datetime to a Julian day."""
   decimal_hour = (
      dt.hour
      + dt.minute / 60.0
      + dt.second / 3600.0
      + dt.microsecond / 3600000000.0
   )

   return swe.julday(
      dt.year,
      dt.month,
      dt.day,
      decimal_hour,
      swe.GREG_CAL
   )


#
# Astronomical longitude calculation.
# Planetary bodies use Swiss Ephemeris directly.
# ASC and MC use Swiss Ephemeris house calculations.
#

# Calculate the zodiac longitude for a body or angular point.
def body_longitude(jd, body_name, tz_name):
   if body_name in BODY_IDS:
      result = swe.calc_ut(
         jd,
         BODY_IDS[body_name],
         FLAGS
      )
      return result[0][0] % 360.0

   latitude, longitude = timezone_coordinates(tz_name)

   houses = swe.houses_ex(
      jd,
      latitude,
      longitude,
      b"P"
   )

   ascmc = houses[1]

   if body_name == "Ascendant":
      return ascmc[0] % 360.0

   if body_name == "MC":
      return ascmc[1] % 360.0

   if body_name == "Descendant":
      return (ascmc[0] + 180.0) % 360.0

   if body_name == "IC":
      return (ascmc[1] + 180.0) % 360.0

   raise ValueError("Unknown astronomical body or point.")

#
# Angular displacement.
# Return the forward angle from one longitude to another.
#

# Return the forward angular distance between two longitudes.
def forward_angle(a, b):
   return (b - a) % 360.0


#
# Body progression calculation.
# Accumulate the actual ephemeris motion without losing 0-degree crossings.
#

# Calculate accumulated body progression between two Julian dates.
def body_progression(
   origin_jd, current_jd, body_name, tz_name
):
   span = current_jd - origin_jd

   if span <= 0:
      return 0.0

   steps = max(1, int(span))
   step = span / steps

   previous = body_longitude(
      origin_jd,
      body_name,
      tz_name
   )
   total = 0.0

   for index in range(1, steps + 1):
      jd = origin_jd + index * step

      current = body_longitude(
         jd,
         body_name,
         tz_name
      )

      total += forward_angle(
         previous,
         current
      )

      previous = current

   return total


#
# Next alignment search.
# Uses TargetDateFinder to find the next target date.
#

# Find the next alignment for the requested longitudinal increment.
def find_next_alignment(
   parent: tk.Misc, origin_jd: float, current_jd: float,
   degree_multiple: float, body_name: str, tz_name: str
) -> tuple[float, float, float]:
   start_longitude: float = body_longitude(origin_jd, body_name, tz_name)

   finder = TargetDateFinder(
      parent=parent,
      start_jd=origin_jd,
      start_longitude=start_longitude,
      current_jd=current_jd,
      inc_longitude=degree_multiple,
      body_name=body_name,
      tz_name=tz_name
   )

   alignment_jd = finder.find_target_date()

   target_progress = finder.running_longitude
   target_longitude = finder.running_longitude % 360.0

   return (
      alignment_jd,
      target_progress,
      target_longitude
   )


#
# Date and time input.
# A blank time means 00:00 in the selected timezone.
#

# Parse local date/time input and convert it to UTC.
def parse_local_datetime(date_text, time_text, tz_name):
   if not date_text:
      raise ValueError("Please select a date.")

   try:
      local_date = datetime.strptime(
         date_text,
         "%Y-%m-%d"
      ).date()
   except ValueError:
      raise ValueError(
         "Date must be in YYYY-MM-DD format."
      )

   if not time_text.strip():
      local_time = datetime.min.time()

   else:
      try:
         local_time = datetime.strptime(
            time_text.strip(),
            "%H:%M"
         ).time()
      except ValueError:
         raise ValueError(
            "Time must be in HH:mm format."
         )

   local_dt = datetime.combine(
      local_date,
      local_time
   )

   return local_dt, local_to_utc(
      local_dt,
      tz_name
   )


#
# Formatting helpers.
#

# Format a datetime for display.
def format_datetime(dt):
   return dt.strftime("%Y-%m-%d %H:%M")


# Format a decimal longitude as degrees.
def format_degrees(value):
   return f"{value:.4f}°"


# Format a longitude as degrees, zodiac sign, minutes and seconds.
def format_zodiac_position(value):
   value %= 360.0

   sign_index = int(value // 30.0)
   sign_degree = value % 30.0

   degrees = int(sign_degree)
   minutes_float = (sign_degree - degrees) * 60.0
   minutes = int(minutes_float)
   seconds = round(
      (minutes_float - minutes) * 60.0
   )

   if seconds >= 60:
      seconds = 0
      minutes += 1

   if minutes >= 60:
      minutes = 0
      degrees += 1

   if degrees >= 30:
      degrees = 0
      sign_index = (sign_index + 1) % 12

   return (
      f"{degrees}° {ZODIAC_SIGNS[sign_index]} "
      f"{minutes:02d}' {seconds:02d}\""
   )

#
# Target date finder.
# Finds the date for a requested longitudinal progression.
#
class TargetDateFinder:
   SHOW_UI_REVOLUTIONS: int = 10

   # Default constructor.
   def __init__(
      self, parent: tk.Misc, start_jd: float,
      start_longitude: float, current_jd: float,
      inc_longitude: float, body_name: str, tz_name: str
   ) -> None:
      # UI.
      self.parent: tk.Misc = parent

      # Store the calculation inputs.
      self.start_jd: float = start_jd
      self.start_longitude: float = start_longitude
      self.current_jd: float = current_jd
      self.inc_longitude: float = inc_longitude
      self.body_name: str = body_name
      self.tz_name: str = tz_name

      # Initialize the running calculation state.
      self.revolutions: int = 0
      self.running_jd: float = start_jd
      self.running_longitude: float = start_longitude

      # Enable the progress UI for long-running calculations.
      self.log_window: tk.Toplevel | None = None
      self.log_text: tk.Text | None = None

   #
   # Progress log.
   # Provides the modal read-only window and logging support.
   #

   # Shows the progress log window.
   def show_log(self) -> None:
      if self.log_window is not None:
         return

      self.log_window = tk.Toplevel(self.parent)
      self.log_window.title("Progress")
      self.log_window.geometry("600x400")
      self.log_window.transient(self.parent)
      self.log_window.grab_set()

      self.log_text = tk.Text(
         self.log_window,
         state=tk.DISABLED,
         wrap=tk.WORD
      )
      self.log_text.pack(
         fill=tk.BOTH,
         expand=True,
         padx=10,
         pady=10
      )

      close_button = tk.Button(
         self.log_window,
         text="Close",
         command=self._close_log
      )
      close_button.pack(pady=(0, 10))

   # Closes the log window.
   def _close_log(self) -> None:
      if self.log_window is None:
         return

      self.log_window.grab_release()
      self.log_window.destroy()
      self.log_window = None
      self.log_text = None

   # Sends a log message to the log window.
   def log(self, message: str) -> None:
      if not self.log_window or self.log_text is None:
         return

      self.log_text.config(state=tk.NORMAL)
      self.log_text.insert(tk.END, f"{message}\n")
      self.log_text.see(tk.END)
      self.log_text.config(state=tk.DISABLED)
      self.log_text.update_idletasks()

   #
   # Common longitude calculations.
   #

   # Uses binary search to find the date when the body reaches the
   # target longitude within the supplied date range.
   # Example: searches from 2021 to 2022 for the date the Sun reaches
   # 699.583°, which represents 339.583° after one complete revolution.
   # Note: This binary search does not support a lower and upper jd that
   # are more than 360 degrees away from each other. In fact, this is
   # solely used to home in a specific value and therefore it is not
   # expected that there will be such a huge variance between the two.
   def _binary_search_longitude(
      self, lower_jd: float, upper_jd: float, target_longitude: float
   ) -> float:
      # Find the longitude relative value to 0 degrees.
      target_longitude_relative: float = target_longitude % 360
      revolution_prefix: float = 0.0
      if target_longitude > 360.0:
         # Determine revolutions prefix. This is the prefix that
         # offsets all the previous revolutions out of target_longitude.
         revolution_prefix = target_longitude - target_longitude_relative

      # Get the body's longitude at each boundary.
      lower_longitude: float = body_longitude(
         lower_jd, self.body_name, self.tz_name
      )
      upper_longitude: float = body_longitude(
         upper_jd, self.body_name, self.tz_name
      )

      # Fix 0 degree overlaps.
      if lower_longitude > target_longitude_relative:
         lower_longitude -= 360.0
      if upper_longitude < target_longitude_relative:
         upper_longitude += 360.0

      # Relocate to absolute position.
      lower_longitude += revolution_prefix
      upper_longitude += revolution_prefix

      # Track the distance from each boundary to the target.
      lower_difference: float = target_longitude - lower_longitude
      upper_difference: float = upper_longitude - target_longitude

      # Narrow the date range using binary search.
      while lower_jd != upper_jd:
         middle_jd: float = (
            lower_jd + (upper_jd - lower_jd) / 2.0
         )

         # Stop when floating-point precision prevents another split.
         if middle_jd == lower_jd or middle_jd == upper_jd:
            break

         # Get the body's longitude at the midpoint.
         middle_longitude: float = body_longitude(
            middle_jd, self.body_name, self.tz_name
         )

         # Resolve middle longitude. We basically assign to abs_middle the
         # closest value to the middle of the actual middle longitude bounds.
         middles: list[float] = [
            revolution_prefix + middle_longitude - 360,
            revolution_prefix + middle_longitude,
            revolution_prefix + middle_longitude + 360
         ]
         abs_mid_upper_lower: float = (
            lower_longitude +
            (upper_longitude - lower_longitude) / 2.0
         )
         abs_middle: float = min(
            middles,
            key=lambda middle: abs(middle - abs_mid_upper_lower)
         )

         # Return immediately if the target longitude is matched.
         if abs_middle == target_longitude:
            return middle_jd

         # Keep the half containing the target longitude.
         if abs_middle < target_longitude:
            lower_jd = middle_jd
            lower_longitude = abs_middle
            lower_difference = target_longitude - lower_longitude
         else:
            upper_jd = middle_jd
            upper_longitude = abs_middle
            upper_difference = upper_longitude - target_longitude

      # Return whichever boundary is closest to the target.
      if lower_difference <= upper_difference:
         return lower_jd

      return upper_jd

   #
   # Target date finder. Combines step 1 and 2 to find the date.
   #

   # Finds the target date using revolutions followed by precise searching.
   def find_target_date(self) -> float:
      self._identify_revolutions()

      if self.revolutions > 0:
         self._find_revolutions()

      jd: float = self._find_target()
      self._close_log()
      return jd

   #
   # Step 1: Identify required revolutions.
   # Estimate the minimum complete revolutions before the detailed search.
   #

   # Identifies the number of complete revolutions to skip.
   def _identify_revolutions(self) -> int:
      elapsed_days: float = self.current_jd - self.start_jd

      if elapsed_days <= MAX_DAYS_BODY_REVOLUTION[self.body_name]:
         return 0

      self.revolutions = int(
         elapsed_days / MAX_DAYS_BODY_REVOLUTION[self.body_name]
      )

      if self.revolutions > self.SHOW_UI_REVOLUTIONS:
         self.show_log()

      return self.revolutions

   # Go through the calculated revolutions and find the date for each
   # revolution.
   def _find_revolutions(self) -> None:
      for _ in range(self.revolutions):
         # Increment the accumulated longitude by one complete revolution.
         self.running_longitude += 360.0

         # Find the date corresponding to the new accumulated longitude.
         self.running_jd = self._find_next_revolution(
            self.running_jd,
            self.start_longitude
         )

         self.log(
            f"Next 360 deg revolution at "
            f"{self.running_longitude:.6f} is "
            f"{self.running_jd:.6f}"
         )

   # _find_next_revolution() needs to rotate the zodiac by 360 degrees from
   # the start_jd. The zodiac longitude of the start_jd would be provided in
   # offset_longitude. This cannot be more than 360 degrees.
   # The function then needs to account for variances in the body's motion.
   # To do that, it adds a minimum number of days covered by a revolution to
   # the start date. It also adds a potential maximum number of days made by
   # a revolution. It then gets these values and binary searches between them
   # the day which aligns with the offset_longitude. That would have found
   # the accurate date between that range that ends the 360 degree turn.
   # Parameters.
   # start_jd: date to start from to find the next body revolution date.
   # offset_longitude would be a degree offset from the 0 degree mark.
   #  This will be modded 360 later on so if you are passing a 360 degree
   #  incremented value, it will be normalized to the right offset. Ex:
   #  If you had 339 degrees and added 360 degrees and pass that value,
   #  This will be modded to 360 to get 339 back.
   # Finds the next date where the body returns to the target longitude.
   def _find_next_revolution(
      self, start_jd: float, offset_longitude: float
   ) -> float:
      min_days: float = MIN_DAYS_BODY_REVOLUTION[self.body_name]
      max_days: float = MAX_DAYS_BODY_REVOLUTION[self.body_name]

      # Establish the time range containing the next revolution.
      lower_jd: float = start_jd + min_days
      upper_jd: float = start_jd + max_days

      # Find the target longitude within the revolution date range.
      return self._binary_search_longitude(
         lower_jd,
         upper_jd,
         offset_longitude
      )

   #
   # Step 2: Refine further.
   # Continue incrementing until the current date is reached or expired.
   #

   # Increment until the target date reaches or passes the current date.
   def _find_target(self) -> float:
      not_found: bool = (
         self.running_jd < self.current_jd or self.running_jd == self.start_jd
      )

      while not_found:
         target_longitude: float = self.running_longitude + self.inc_longitude
         target_jd: float = self._binary_search_longitude(
            self.running_jd,
            self.running_jd + MAX_DAYS_BODY_REVOLUTION[self.body_name],
            target_longitude
         )
         self.log(f"Next target at {target_longitude:.6f} is {target_jd:.6f}")

         self.running_jd = target_jd
         self.running_longitude = target_longitude

         # Found?
         not_found: bool = (
            self.running_jd < self.current_jd or
            self.running_jd == self.start_jd
         )

      return self.running_jd

#
# Main application.
#

class SolarProgressionApp:
   def __init__(self, root):
      self.root = root
      self.root.title("Zodiac Progression")
      self.root.resizable(False, False)

      self.degree_values = []

      self.build_ui()

   #
   # Build the main interface.
   #

   def build_ui(self):
      main = ttk.Frame(
         self.root,
         padding=12
      )
      main.grid(
         row=0,
         column=0,
         sticky="nsew"
      )

      #
      # Date and time section.
      #

      date_frame = ttk.LabelFrame(
         main,
         text="Date and Time",
         padding=10
      )
      date_frame.grid(
         row=0,
         column=0,
         padx=4,
         pady=4,
         sticky="ew"
      )

      ttk.Label(
         date_frame,
         text="Start Date:"
      ).grid(
         row=0,
         column=0,
         padx=4,
         pady=4,
         sticky="w"
      )

      self.start_date_var = tk.StringVar()

      self.start_date = DateEntry(
         date_frame,
         textvariable=self.start_date_var,
         date_pattern="yyyy-mm-dd",
         width=13
      )
      self.start_date.grid(
         row=0,
         column=1,
         padx=4,
         pady=4
      )
      self.start_date_var.set("")

      ttk.Label(
         date_frame,
         text="Start Time:"
      ).grid(
         row=0,
         column=2,
         padx=4,
         pady=4,
         sticky="w"
      )

      self.start_time_var = tk.StringVar()

      ttk.Entry(
         date_frame,
         textvariable=self.start_time_var,
         width=8
      ).grid(
         row=0,
         column=3,
         padx=4,
         pady=4
      )

      ttk.Label(
         date_frame,
         text="Current Date:"
      ).grid(
         row=1,
         column=0,
         padx=4,
         pady=4,
         sticky="w"
      )

      self.current_date_var = tk.StringVar()

      self.current_date = DateEntry(
         date_frame,
         textvariable=self.current_date_var,
         date_pattern="yyyy-mm-dd",
         width=13
      )
      self.current_date.grid(
         row=1,
         column=1,
         padx=4,
         pady=4
      )
      self.current_date_var.set("")

      ttk.Label(
         date_frame,
         text="Current Time:"
      ).grid(
         row=1,
         column=2,
         padx=4,
         pady=4,
         sticky="w"
      )

      self.current_time_var = tk.StringVar()

      ttk.Entry(
         date_frame,
         textvariable=self.current_time_var,
         width=8
      ).grid(
         row=1,
         column=3,
         padx=4,
         pady=4
      )

      ttk.Label(
         date_frame,
         text="Timezone:"
      ).grid(
         row=2,
         column=0,
         padx=4,
         pady=4,
         sticky="w"
      )

      zone_values = list(COMMON_TIMEZONES)

      self.timezone_var = tk.StringVar(
         value="UTC"
      )

      self.timezone_box = ttk.Combobox(
         date_frame,
         textvariable=self.timezone_var,
         values=zone_values,
         width=34,
         state="normal"
      )
      self.timezone_box.grid(
         row=2,
         column=1,
         columnspan=3,
         padx=4,
         pady=4,
         sticky="ew"
      )

      #
      # Astronomical body/point selection.
      #

      ttk.Label(
         date_frame,
         text="Zodiac Body/Point:"
      ).grid(
         row=3,
         column=0,
         padx=4,
         pady=4,
         sticky="w"
      )

      self.body_var = tk.StringVar(
         value="Sun — (360° = ~365.24 days)"
      )

      self.body_box = ttk.Combobox(
         date_frame,
         textvariable=self.body_var,
         values=list(BODY_OPTIONS.keys()),
         width=34,
         state="readonly"
      )
      self.body_box.grid(
         row=3,
         column=1,
         columnspan=3,
         padx=4,
         pady=4,
         sticky="ew"
      )

      #
      # Degree section.
      #

      degree_frame = ttk.LabelFrame(
         main,
         text="Next Zodiac Increment by Degrees",
         padding=10
      )
      degree_frame.grid(
         row=1,
         column=0,
         padx=4,
         pady=4,
         sticky="ew"
      )

      ttk.Label(
         degree_frame,
         text="Degree Increment:"
      ).grid(
         row=0,
         column=0,
         padx=4,
         pady=4,
         sticky="w"
      )

      self.degree_var = tk.StringVar()

      ttk.Entry(
         degree_frame,
         textvariable=self.degree_var,
         width=10
      ).grid(
         row=0,
         column=1,
         padx=4,
         pady=4
      )

      ttk.Button(
         degree_frame,
         text="Add",
         command=self.add_degree
      ).grid(
         row=0,
         column=2,
         padx=4,
         pady=4
      )

      ttk.Button(
         degree_frame,
         text="Remove",
         command=self.remove_degree
      ).grid(
         row=0,
         column=3,
         padx=4,
         pady=4
      )

      self.degree_list = tk.Listbox(
         degree_frame,
         height=5,
         width=30
      )
      self.degree_list.grid(
         row=1,
         column=0,
         columnspan=4,
         padx=4,
         pady=4,
         sticky="ew"
      )

      #
      # Action buttons.
      #

      button_frame = ttk.Frame(main)
      button_frame.grid(
         row=2,
         column=0,
         padx=4,
         pady=8,
         sticky="ew"
      )

      ttk.Button(
         button_frame,
         text="Calculate",
         command=self.calculate
      ).grid(
         row=0,
         column=0,
         padx=4
      )

      ttk.Button(
         button_frame,
         text="Clear",
         command=self.clear
      ).grid(
         row=0,
         column=1,
         padx=4
      )

      button_frame.columnconfigure(
         2,
         weight=1
      )

      ttk.Button(
         button_frame,
         text="Load",
         command=self.load_state
      ).grid(
         row=0,
         column=3,
         padx=4
      )

      ttk.Button(
         button_frame,
         text="Save",
         command=self.save_state
      ).grid(
         row=0,
         column=4,
         padx=4
      )

      ttk.Button(
         button_frame,
         text="?",
         width=3,
         command=self.show_about
      ).grid(
         row=0,
         column=5,
         padx=(4, 0)
      )

   #
   # About window.
   #

   # Display the application information.
   def show_about(self) -> None:
      window = tk.Toplevel(self.root)
      window.title("About astrodates")
      window.resizable(False, False)
      window.transient(self.root)

      content = ttk.Frame(
         window,
         padding=12
      )
      content.grid(
         row=0,
         column=0,
         sticky="nsew"
      )

      image_frame = tk.Frame(
         content,
         width=128,
         height=128,
         borderwidth=0,
         highlightthickness=0,
         bg=window.cget("background")
      )
      image_frame.grid(
         row=0,
         column=0,
         padx=(0, 12),
         sticky="n"
      )
      image_frame.grid_propagate(False)

      image_path = os.path.join(
         os.path.dirname(os.path.abspath(__file__)),
         "astrodates.png"
      )

      try:
         about_image = tk.PhotoImage(
            file=image_path
         )
      except tk.TclError:
         about_image = None

      if about_image is not None:
         image_label = tk.Label(
            image_frame,
            image=about_image,
            borderwidth=0,
            highlightthickness=0,
            bg=window.cget("background")
         )
         image_label.image = about_image
         image_label.pack()

      text = tk.Text(
         content,
         width=70,
         height=13,
         wrap=tk.WORD,
         relief=tk.FLAT,
         borderwidth=0,
         highlightthickness=0,
         bg=window.cget("background")
      )
      text.grid(
         row=0,
         column=1,
         sticky="nw"
      )

      text.tag_configure(
         "heading",
         font=("TkDefaultFont", 16, "bold")
      )
      text.tag_configure(
         "bold",
         font=("TkDefaultFont", 10, "bold")
      )
      text.tag_configure(
         "link",
         underline=True,
         font=("TkFixedFont", 10)
      )

      text.insert(
         tk.END,
         "astrodates\n\n",
         "heading"
      )
      text.insert(
         tk.END,
         f"{VERSION}\n"
         "Copyright Duncan Camilleri 2026\n",
         "bold"
      )
      text.insert(
         tk.END,
         "https://github.com/dnc77\n\n",
         "link"
      )
      text.insert(
         tk.END,
         "astrodates is a small application that finds when certain "
         "planetary bodies align at a certain degree along the zodiac. "
         "It accepts a start date and degree increments that are factors "
         "of 360 degrees. It finds the position of the planetary body "
         "at that start date and for every degree value specified, it "
         "starts incrementing by that degree amount until it reaches "
         "or exceeds a current date. It then reports the date when the "
         "planetary body will align with that position."
      )

      text.configure(
         state=tk.DISABLED
      )

      ttk.Button(
         content,
         text="OK",
         command=window.destroy
      ).grid(
         row=1,
         column=0,
         columnspan=2,
         pady=(12, 0)
      )

      window.protocol(
         "WM_DELETE_WINDOW",
         window.destroy
      )

      window.update_idletasks()
      window.lift()
      window.focus_force()
      window.grab_set()

   #
   # Add a degree increment.
   #

   def add_degree(self):
      text = self.degree_var.get().strip()

      try:
         value = float(text)
      except ValueError:
         messagebox.showerror(
            "Invalid Degree",
            "Enter a valid number of degrees.",
            parent=self.root
         )
         return

      if value <= 0 or value > 360:
         messagebox.showerror(
            "Invalid Degree",
            "Degree increment must be greater than 0 and "
            "no more than 360.",
            parent=self.root
         )
         return

      if value in self.degree_values:
         return

      self.degree_values.append(value)
      self.degree_values.sort()

      self.refresh_degree_list()
      self.degree_var.set("")

   #
   # Remove the selected degree increment.
   #

   def remove_degree(self):
      selected = list(
         self.degree_list.curselection()
      )

      for index in reversed(selected):
         del self.degree_values[index]

      self.refresh_degree_list()

   #
   # Refresh the degree list.
   #

   def refresh_degree_list(self):
      self.degree_list.delete(
         0,
         tk.END
      )

      for value in self.degree_values:
         self.degree_list.insert(
            tk.END,
            format_degrees(value)
         )

   #
   # Save the current application settings to an ASD file.
   #

   def save_state(self):
      path = filedialog.asksaveasfilename(
         parent=self.root,
         title="Save Settings",
         defaultextension=".asd",
         filetypes=[
            ("ASD files", "*.asd"),
            ("All files", "*.*")
         ]
      )

      if not path:
         return

      data = {
         "start_date": self.start_date_var.get(),
         "start_time": self.start_time_var.get(),
         "current_date": self.current_date_var.get(),
         "current_time": self.current_time_var.get(),
         "timezone": self.timezone_var.get(),
         "body": self.body_var.get(),
         "degrees": self.degree_values
      }

      try:
         with open(
            path,
            "w",
            encoding="utf-8"
         ) as file:
            json.dump(
               data,
               file,
               indent=3
            )

         messagebox.showinfo(
            "Save Complete",
            f"Settings saved to:\n{path}",
            parent=self.root
         )

      except (OSError, TypeError, ValueError) as error:
         messagebox.showerror(
            "Save Error",
            str(error),
            parent=self.root
         )

   #
   # Load application settings from an ASD file.
   #

   def load_state(self):
      path = filedialog.askopenfilename(
         parent=self.root,
         title="Load Settings",
         filetypes=[
            ("ASD files", "*.asd"),
            ("All files", "*.*")
         ]
      )

      if not path:
         return

      try:
         with open(
            path,
            "r",
            encoding="utf-8"
         ) as file:
            data = json.load(file)

         if not isinstance(data, dict):
            raise ValueError(
               "The selected ASD file is not valid."
            )

         start_date = data.get("start_date", "")
         start_time = data.get("start_time", "")
         current_date = data.get("current_date", "")
         current_time = data.get("current_time", "")
         timezone_name = data.get("timezone", "UTC")
         body = data.get(
            "body",
            "Sun — (360° = ~365.24 days)"
         )
         degrees = data.get("degrees", [])

         if not isinstance(degrees, list):
            raise ValueError(
               "The degree list in the ASD file is invalid."
            )

         if body not in BODY_OPTIONS:
            raise ValueError(
               "The selected zodiac body/point is invalid."
            )

         if timezone_name not in COMMON_TIMEZONES:
            raise ValueError(
               "The timezone in the ASD file is unavailable."
            )

         loaded_degrees = []

         for value in degrees:
            value = float(value)

            if value <= 0 or value > 360:
               raise ValueError(
                  "The ASD file contains an invalid degree."
               )

            if value not in loaded_degrees:
               loaded_degrees.append(value)

         loaded_degrees.sort()

         self.start_date_var.set(start_date)
         self.start_time_var.set(start_time)
         self.current_date_var.set(current_date)
         self.current_time_var.set(current_time)
         self.timezone_var.set(timezone_name)
         self.body_var.set(body)

         self.degree_values = loaded_degrees
         self.refresh_degree_list()

         messagebox.showinfo(
            "Load Complete",
            f"Settings loaded from:\n{path}",
            parent=self.root
         )

      except (
         OSError,
         json.JSONDecodeError,
         TypeError,
         ValueError
      ) as error:
         messagebox.showerror(
            "Load Error",
            str(error),
            parent=self.root
         )

   #
   # Calculate results using the selected body or angular point.
   #
   # Calculate the progression results.
   def calculate(self):
      try:
         timezone_name = self.timezone_var.get().strip()

         start_local, start_utc = parse_local_datetime(
            self.start_date_var.get().strip(),
            self.start_time_var.get(),
            timezone_name
         )

         current_local, current_utc = parse_local_datetime(
            self.current_date_var.get().strip(),
            self.current_time_var.get(),
            timezone_name
         )

         if current_utc < start_utc:
            raise ValueError(
               "Current date/time must not be before the "
               "start date/time."
            )

         if not self.degree_values:
            raise ValueError(
               "Add at least one degree increment."
            )

         body_name = BODY_OPTIONS[
            self.body_var.get()
         ]

         origin_jd = julian_day(start_utc)
         current_jd = julian_day(current_utc)

         origin_longitude = body_longitude(
            origin_jd,
            body_name,
            timezone_name
         )

         current_longitude = body_longitude(
            current_jd,
            body_name,
            timezone_name
         )

         current_progress = body_progression(
            origin_jd,
            current_jd,
            body_name,
            timezone_name
         )

         results = []

         for degree in self.degree_values:
            (
               alignment_jd, target_progress, target_longitude
            ) = find_next_alignment(
               self.root, origin_jd, current_jd,
               degree, body_name, timezone_name
            )

            alignment_utc = swe.revjul(alignment_jd, swe.GREG_CAL)

            alignment_dt = datetime(
               int(alignment_utc[0]), int(alignment_utc[1]),
               int(alignment_utc[2])
            )

            day_fraction = alignment_utc[3]
            seconds = round(day_fraction * 3600.0)

            if seconds >= 86400:
               alignment_dt += timedelta(days=1)
               seconds -= 86400

            alignment_dt += timedelta(seconds=seconds)

            alignment_local = utc_to_local(alignment_dt, timezone_name)

            alignment_body_longitude = body_longitude(
               alignment_jd, body_name, timezone_name
            )

            results.append(
               {
                  "degree": degree,
                  "progress": target_progress,
                  "revolutions": (target_progress / 360.0),
                  "target_longitude": target_longitude,
                  "alignment": alignment_local,
                  "body_longitude": (alignment_body_longitude)
               }
            )

         self.show_results(start_local, current_local, body_name,
            origin_longitude, current_longitude, current_progress,
            results
         )

      except Exception as error:
         messagebox.showerror(
            "Calculation Error",
            str(error),
            parent=self.root
         )

   #
   # Show the result table.
   # The selected body/point is reflected throughout the report.
   #

   # Display the calculation results in a child window.
   def show_results(
      self,
      start_local,
      current_local,
      body_name,
      origin_longitude,
      current_longitude,
      current_progress,
      results
   ):
      window = tk.Toplevel(self.root)
      window.title(
         f"{body_name} Progression Results"
      )
      window.resizable(True, True)

      #
      # Make the result window a true child of the main window.
      # transient() keeps it associated with the parent, while grab_set()
      # prevents interaction with the parent until this window is closed.
      #

      window.transient(self.root)

      frame = ttk.Frame(
         window,
         padding=12
      )
      frame.grid(
         row=0,
         column=0,
         sticky="nsew"
      )

      summary = (
         f"Body/Point: {body_name}\n"
         f"Start: {format_datetime(start_local)}  |  "
         f"Current: {format_datetime(current_local)}\n"
         f"Start {body_name}: "
         f"{format_degrees(origin_longitude)}  |  "
         f"Current {body_name}: "
         f"{format_degrees(current_longitude)}  |  "
         f"Progression: "
         f"{format_degrees(current_progress)}\n"
         f"Start {body_name} Position: "
         f"{format_zodiac_position(origin_longitude)}  |  "
         f"Current {body_name} Position: "
         f"{format_zodiac_position(current_longitude)}"
      )

      ttk.Label(
         frame,
         text=summary,
         justify="left"
      ).grid(
         row=0,
         column=0,
         columnspan=2,
         padx=4,
         pady=(0, 8),
         sticky="w"
      )

      columns = (
         "degree",
         "offset",
         "revolutions",
         "target_longitude",
         "alignment",
         "body_position"
      )

      table = ttk.Treeview(
         frame,
         columns=columns,
         show="headings",
         height=min(
            15,
            max(3, len(results))
         )
      )

      table.heading(
         "degree",
         text="Degree Increment"
      )

      table.heading(
         "offset",
         text="Degree Offset"
      )

      table.heading(
         "revolutions",
         text="Revolutions"
      )

      table.heading(
         "target_longitude",
         text=f"Target {body_name} Longitude"
      )

      table.heading(
         "alignment",
         text="Next Alignment"
      )

      table.heading(
         "body_position",
         text=f"{body_name} Position"
      )

      table.column(
         "degree",
         width=110,
         anchor="center"
      )

      table.column(
         "offset",
         width=105,
         anchor="center"
      )

      table.column(
         "revolutions",
         width=90,
         anchor="center"
      )

      table.column(
         "target_longitude",
         width=145,
         anchor="center"
      )

      table.column(
         "alignment",
         width=175,
         anchor="center"
      )

      table.column(
         "body_position",
         width=160,
         anchor="center"
      )

      for result in results:
         table.insert(
            "",
            tk.END,
            values=(
               format_degrees(
                  result["degree"]
               ),
               format_degrees(
                  result["progress"]
               ),
               f'{result["revolutions"]:.4f}',
               format_degrees(
                  result["target_longitude"]
               ),
               format_datetime(
                  result["alignment"]
               ),
               format_zodiac_position(
                  result["body_longitude"]
               )
            )
         )

      table.grid(
         row=1,
         column=0,
         columnspan=2,
         padx=4,
         pady=4,
         sticky="nsew"
      )

      scrollbar = ttk.Scrollbar(
         frame,
         orient="vertical",
         command=table.yview
      )

      scrollbar.grid(
         row=1,
         column=2,
         sticky="ns"
      )

      table.configure(
         yscrollcommand=scrollbar.set
      )

      #
      # Export the visible table.
      #

      ttk.Button(
         frame,
         text="Export Text",
         command=lambda: self.export_text(
            table,
            columns,
            summary,
            window,
         ),
      ).grid(
         row=2,
         column=0,
         padx=4,
         pady=8,
         sticky="w",
      )

      ttk.Button(
         frame,
         text="Close",
         command=lambda: self.close_child(
            window
         ),
      ).grid(
         row=2,
         column=1,
         padx=4,
         pady=8,
         sticky="e",
      )

      window.columnconfigure(
         0,
         weight=1,
      )

      window.rowconfigure(
         0,
         weight=1,
      )

      frame.columnconfigure(
         0,
         weight=1,
      )

      frame.rowconfigure(
         1,
         weight=1
      )

      #
      # Put the child above the parent and make it modal.
      #

      window.protocol(
         "WM_DELETE_WINDOW",
         lambda: self.close_child(window)
      )

      window.update_idletasks()
      window.lift()
      window.focus_force()
      window.grab_set()

   #
   # Close a child window and release its input grab.
   #

   # Close a child window and release its input grab.
   def close_child(self, window):
      try:
         window.grab_release()
      except tk.TclError:
         pass

      if window.winfo_exists():
         window.destroy()

   #
   # Export the displayed report, including the summary.
   #

   # Export the displayed report as a text file.
   def export_text(
      self, table, columns, summary, parent
   ):
      path = filedialog.asksaveasfilename(
         parent=parent,
         title="Export Results",
         defaultextension=".txt",
         filetypes=[
            ("Text files", "*.txt"),
            ("All files", "*.*")
         ]
      )

      if not path:
         return

      headers = [
         table.heading(column)["text"]
         for column in columns
      ]

      lines = [
         summary,
         "",
         "\t".join(headers)
      ]

      for item in table.get_children():
         values = table.item(
            item,
            "values"
         )

         lines.append(
            "\t".join(
               str(value)
               for value in values
            )
         )

      try:
         with open(
            path,
            "w",
            encoding="utf-8",
            newline=""
         ) as file:
            file.write(
               "\n".join(lines)
            )

         messagebox.showinfo(
            "Export Complete",
            f"Results exported to:\n{path}",
            parent=parent
         )

      except OSError as error:
         messagebox.showerror(
            "Export Error",
            str(error),
            parent=parent,
         )

   #
   # Clear the complete form.
   #

   # Clear all input fields and degree selections.
   def clear(self):
      self.start_date_var.set("")
      self.current_date_var.set("")
      self.start_time_var.set("")
      self.current_time_var.set("")
      self.degree_var.set("")
      self.timezone_var.set("UTC")
      self.body_var.set(
         "Sun — (360° = ~365.24 days)"
      )

      self.degree_values.clear()
      self.refresh_degree_list()


#
# Application entry point.
#

# Start the application.
def main():
   root = tk.Tk()
   SolarProgressionApp(root)
   root.mainloop()


if __name__ == "__main__":
   main()

