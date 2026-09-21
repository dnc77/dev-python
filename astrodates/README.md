# Zodiac Progression Application Overview

## 1. Objective

The objective of this application is to find out when a particular body reaches a particular point in the sky.
There are various real-world applications for this purpose which is beyond scope here.

On a particular start date and location, along the 360° of the zodiac, the objective of the application is to calculate the date and time when a body moves in increments of a degree increment until a particular current date is reached. The degree increment must be a multiplicative factor of 360. This is important because the application first measures whole revolutions to a closer date to the current date for performance reasons.

***IMPORTANT NOTE:***

While this application has been written mostly with the help of `LLM's` and `AI` coding assistances, some sensitive areas have been scrutinized and had to be rewritten carefully.
Albeit, this product is considered to be a **prototype**. Some initial tests have been conducted but it is subject to more intense testing.

## 2. Getting the application to run

This was written in `Python` using version `3.14.4` and tested on Linux.
Another version exists modified to work on `Windows 7` using `Python 3.8.2`.

### Running using `Python`
1. Install `Python`.
2. Create a virtual environment: `python3 -m venv venv`.
3. Source the virtual environment.
   - In Windows: `venv/Scripts/activate.bat`.
   - In Linux: `. venv/bin/activate`.
4. Install the dependencies from the requirements file: `pip install -r requirements.txt`.
5. Run using `python astrodates.py`

## 3. Application Files

The application consists primarily of:

* `astrodates.py`
* `timezone_api.py`

---

## 4. `timezone_api.py`

This is the timezone layer.

It provides:

* `COMMON_TIMEZONES`
* `local_to_utc()`
* `utc_to_local()`
* `timezone_coordinates()`

Its responsibilities are:

1. Convert user-entered local date/time to UTC.
2. Convert calculated UTC dates/times back to local time.
3. Provide geographic coordinates associated with the selected timezone.

It does not perform astronomical calculations.

---

# 5. `astrodates.py`

`astrodates.py` contains the main application, including:

* configuration
* astronomical calculations
* progression calculations
* alignment searches
* date/time parsing
* GUI construction
* result display
* save/load
* text export

---

# 6. Configuration

The following constants define the astronomical options:

```text
FLAGS
BODY_OPTIONS
BODY_IDS
ZODIAC_SIGNS
```

## `BODY_OPTIONS`

Defines the bodies and angular points available to the user:

* Sun
* Moon
* Ascendant
* Descendant
* MC
* IC

## `BODY_IDS`

Maps planetary bodies to Swiss Ephemeris IDs.

Currently:

* Sun
* Moon

The angular points are calculated separately using house calculations.

---

# 7. Astronomical Calculation Layer

The main calculation functions are:

```text
julian_day()
body_longitude()
forward_angle()
body_progression()
```

These functions form the mathematical core of the application.

---

## 7.1 `julian_day()`

Converts a naive UTC `datetime` into a Swiss Ephemeris Julian Day.

Flow:

```text
UTC datetime
     |
     v
decimal hour
     |
     v
Swiss Ephemeris Julian Day
```

Swiss Ephemeris calculations use the resulting Julian Day.

---

# 8. `body_longitude()`

Calculates the zodiac longitude of the selected body or angular point.

Flow:

```text
Julian Day
     |
     v
body_longitude()
     |
     +-------------------+
     |                   |
     v                   v
Sun / Moon          ASC / MC / etc.
     |                   |
     v                   v
Swiss Ephemeris     House calculation
     |                   |
     +---------+---------+
               |
               v
        0° to 360° longitude
```

For the Sun and Moon, the function uses:

```text
swe.calc_ut()
```

For the Ascendant, Descendant, MC and IC, it uses:

```text
swe.houses_ex()
```

The result is normalized to the range:

```text
0° <= longitude < 360°
```

---

# 9. `forward_angle()`

Calculates the forward angular distance from one longitude to another.

Conceptually:

```text
longitude A
     |
     v
forward movement around zodiac
     |
     v
longitude B
```

The result is always between:

```text
0° and 360°
```

This allows progression calculations to continue correctly across 0° Aries.

Example:

```text
Start = 350°
Current = 10°

Direct subtraction:

10 - 350 = -340°

Forward angle:

20°
```

---

# 10. `body_progression()`

This is one of the most important functions in the application.

Its purpose is to accumulate the body's actual forward angular movement between the start date and current date.

It does not simply subtract the start longitude from the current longitude.

Instead, it divides the elapsed period into steps and accumulates the forward angular movement between consecutive positions.

Conceptually:

```text
START
  |
  v
Position 1
  |
  v
Position 2
  |
  v
Position 3
  |
  v
Position 4
  |
  ...
  |
  v
CURRENT
```

Each movement is calculated using:

```text
forward_angle(previous, current)
```

and added to a running total.

Therefore, 0° crossings are not lost.

---

## Example

Suppose:

```text
Start longitude   = 279.9136°
Current longitude = 174.1358°
```

The direct difference is:

```text
174.1358 - 279.9136
= -105.7778°
```

The forward angular difference is:

```text
254.2222°
```

But if the body has completed 55 full zodiac cycles since the start, the accumulated progression can be:

```text
55 × 360°
+ 254.2222°
= 20054.2222°
```

Therefore:

```text
Current progression = 20054.2222°
```

This is an unwrapped accumulated progression.

---

# 11. `find_next_alignment()`

This function is responsible for finding the next requested degree alignment.

This is the critical calculation area currently being investigated.

Its intended conceptual flow is:

```text
Current progression
       |
       v
Selected degree increment
       |
       v
Next progression multiple
       |
       v
Target progression
       |
       v
Future date/time when progression
reaches target progression
```

For example:

```text
Current progression = 20054.2222°
Selected increment  = 30°
```

The next 30° multiple is:

```text
20070°
```

Therefore the additional progression required is:

```text
20070°
- 20054.2222°
= 15.7778°
```

The alignment should therefore occur when the accumulated progression reaches:

```text
20070°
```

---

# 12. Target Longitude

The target longitude is derived from:

```text
origin longitude + target progression
```

and normalized to 0°–360°.

For example:

```text
Origin longitude = 279.9136°
Target progression = 20070°
```

Since:

```text
20070° mod 360° = 270°
```

the target longitude is:

```text
279.9136° + 270°
= 549.9136°

549.9136° mod 360°
= 189.9136°
```

Therefore:

```text
Target longitude = 189.9136°
```

---

# 13. Important Distinction

There are two related but different quantities:

## Progression

The accumulated movement since the original start date.

Example:

```text
20054.2222°
```

## Longitude

The body's current position within one zodiac cycle.

Example:

```text
174.1358°
```

Longitude wraps every 360°.

Progression does not.

Therefore:

```text
Longitude:
0° ... 360° ... 0° ... 360°

Progression:
0° ... 360° ... 720° ... 1080° ...
```

The alignment search must preserve this distinction.

---

# 14. `parse_local_datetime()`

Handles user-entered dates and times.

Flow:

```text
User date
+
User time
+
Selected timezone
       |
       v
local datetime
       |
       v
local_to_utc()
       |
       v
UTC datetime
```

The UTC datetime is then converted to a Julian Day by `julian_day()`.

A blank time is interpreted as:

```text
00:00
```

---

# 15. Main GUI Class

The main Tkinter application is:

```text
SolarProgressionApp
```

Its constructor:

```text
__init__()
```

initializes the application and calls:

```text
build_ui()
```

---

# 16. `build_ui()`

Creates the main interface.

The interface contains three main areas.

## Date and Time

Inputs:

* Start Date
* Start Time
* Current Date
* Current Time
* Timezone
* Zodiac Body/Point

## Degree Section

Inputs:

* Degree Increment
* Add
* Remove
* Degree list

## Action Buttons

Buttons:

* Calculate
* Clear
* Load
* Save

---

# 17. Degree Management

## `add_degree()`

Adds a degree increment to the selected list.

Valid values are:

```text
greater than 0°
and
no more than 360°
```

Duplicate values are ignored.

The list is sorted numerically.

## `remove_degree()`

Removes the selected degree increments.

## `refresh_degree_list()`

Updates the visible Tkinter listbox.

---

# 18. `calculate()`

This is the main controller connecting the GUI to the calculation engine.

Its overall flow is:

```text
User presses Calculate
        |
        v
Read GUI inputs
        |
        v
parse_local_datetime()
        |
        v
Start UTC / Current UTC
        |
        v
julian_day()
        |
        +-------------------------+
        |                         |
        v                         v
origin_longitude          current_longitude
        |                         |
        +------------+------------+
                     |
                     v
             body_progression()
                     |
                     v
             current_progress
                     |
                     v
          Loop through degrees
                     |
                     v
          find_next_alignment()
                     |
                     v
                  results
                     |
                     v
              show_results()
```

---

# 19. `show_results()`

Creates the results window.

It displays a summary containing:

```text
Body/Point
Start date/time
Current date/time
Start longitude
Current longitude
Current progression
Start zodiac position
Current zodiac position
```

It then displays the results table.

The table contains:

```text
Degree Increment
Degree Offset
Revolutions
Target Longitude
Next Alignment
Body Position
```

---

# 20. Result Table

Each calculated result contains:

```text
degree
progress
revolutions
target_longitude
alignment
body_longitude
```

The values are formatted for display.

For example:

```text
Degree Increment
30.0000°

Degree Offset
20070.
```

# Zodiac Progression — Simple Terminology Guide

This is a plain-English explanation of the main terms used by the application.

## 1. Planet / Body / Point

The application can calculate the position of:

* **Sun** — the apparent position of the Sun in the zodiac.
* **Moon** — the apparent position of the Moon.
* **MC (Midheaven)** — the zodiac degree at the top of the local sky.

The application calls all of these a **body/point**.

---

## 2. Longitude

**Longitude** is simply the position of something around the 360° zodiac circle.

The zodiac is divided into 12 signs:

```text
Aries       0°–30°
Taurus     30°–60°
Gemini     60°–90°
Cancer     90°–120°
Leo       120°–150°
Virgo     150°–180°
Libra     180°–210°
Scorpio    210°–240°
Sagittarius 240°–270°
Capricorn  270°–300°
Aquarius   300°–330°
Pisces     330°–360°
```

For example:

```text
279.9136°
```

means approximately:

```text
9° Capricorn 54'
```

The application uses the number from **0° to 360°** internally.

---

## 3. Start Longitude

The **Start Longitude** is where the selected body was located at the starting date and time.

For example:

```text
Start Sun: 279.9136°
```

This is the starting point from which the application's progression is measured.

---

## 4. Current Longitude

The **Current Longitude** is where the body is located at the current date and time.

For example:

```text
Current Sun: 174.1358°
```

This is the body's actual zodiac position at the current time.

---

## 5. Movement

Planets are constantly moving through the zodiac.

For example, imagine the Sun starts here:

```text
Capricorn 9°
```

and later is here:

```text
Virgo 24°
```

The application calculates how far the Sun has actually travelled between those two times.

---

## 6. Progression

**Progression** means:

> How many degrees the selected body has travelled since the starting date.

It is **not limited to 0°–360°**.

For example, if something has travelled:

```text
720°
```

that means it has completed:

```text
2 complete revolutions
```

around the zodiac.

If it has travelled:

```text
20,054°
```

that means it has travelled around the zodiac many times, with the final position representing its current location.

This is why the application's progression number can become very large.

---

## 7. Why Progression Can Be Different from Longitude

This is one of the most important concepts in the application.

**Longitude wraps around at 360°.**

For example:

```text
350°
370°
```

are equivalent to:

```text
350°
10°
```

because 370° is one complete revolution plus 10°.

But **progression does not wrap around**.

So the application might say:

```text
Progression: 20,054°
```

while the actual zodiac longitude is only:

```text
174°
```

They are measuring two different things:

* **Longitude** = where the body is now.
* **Progression** = how far the body has travelled since the start.

---

## 8. Revolution

One complete trip around the zodiac is:

```text
360°
```

So:

```text
360° = 1 revolution
720° = 2 revolutions
1080° = 3 revolutions
```

The application calculates:

```text
Revolutions = progression ÷ 360
```

For example:

```text
20,160° ÷ 360 = 56 revolutions
```

---

## 9. Degree Increment

A **degree increment** tells the application what progression milestone you want to find.

For example:

```text
30°
60°
90°
120°
180°
360°
```

If the current progression is:

```text
20,054°
```

and you ask for a **30° increment**, the next multiple of 30 is:

```text
20,070°
```

So the application searches for the time when the body reaches **20,070° of total progression**.

This is why different degree increments can sometimes produce the **same date**.

For example:

```text
30°  → 20,070°
45°  → 20,070°
90°  → 20,070°
```

All three are asking for the same next progression milestone.

---

## 10. Target Progression

The **Target Progression** is the milestone the application is looking for.

Example:

```text
Current Progression: 20,054°
Degree Increment:    30°

Next Target:         20,070°
```

The application then searches forward in time until the selected body reaches that target.

---

## 11. Target Longitude

The target progression can be converted back into a zodiac position.

The application starts with the original longitude and adds the target progression:

```text
Start Longitude
        +
Target Progression
        =
Target Longitude
```

The result is then reduced to the normal 0°–360° zodiac range.

This tells us **where in the zodiac the body should be when that progression milestone is reached**.

---

## 12. Alignment

An **alignment** is simply the date and time when the selected body reaches the requested target.

For example:

```text
Target Progression: 20,070°
Next Alignment:     2026-10-03 02:38
```

This means that, according to the astronomical calculation, the body reaches that progression milestone at that time.

---

## 13. Forward Movement

The application needs to distinguish between:

```text
moving forward
```

and simply comparing two numbers.

For example, moving from:

```text
350°
```

to:

```text
10°
```

does **not** mean the body moved backwards 340°.

It moved forward:

```text
20°
```

The application therefore uses a **forward angle** calculation so that crossing 0° Aries does not break the movement calculation.

---

## 14. Ephemeris

An **ephemeris** is essentially a set of astronomical calculations/data that tells us where astronomical bodies are at particular times.

The application uses **Swiss Ephemeris** to calculate planetary positions.

In simple terms:

> Give Swiss Ephemeris a date and time, and it calculates where the planet is.

---

## 15. Swiss Ephemeris

**Swiss Ephemeris** is the astronomical calculation library used by the application.

The application does not simply guess where the planets are.

It asks Swiss Ephemeris to calculate their positions.

---

## 16. Julian Day

A **Julian Day** is a numerical way of representing a date and time.

Computers doing astronomical calculations commonly use Julian Days because it makes calculating the amount of time between two dates straightforward.

The application therefore converts:

```text
2026-09-17 00:00
```

into a Julian Day before doing the astronomical calculations.

You do not normally need to worry about the actual Julian Day number.

---

## 17. UTC

**UTC** is the world's standard reference time.

The application converts the user's selected local time into UTC before asking Swiss Ephemeris for the astronomical position.

For example:

```text
Melbourne local time
        ↓
UTC
        ↓
Swiss Ephemeris
        ↓
Planet position
```

This prevents different time zones from producing inconsistent astronomical calculations.

---

## 18. Timezone

A timezone tells the application what local clock time means at a particular location.

For example:

```text
Australia/Melbourne
America/New_York
Europe/London
Asia/Tokyo
```

The timezone is important because:

```text
2026-09-17 12:00 Melbourne
```

and:

```text
2026-09-17 12:00 London
```

are different actual moments in time.

---

## 19. Daylight Saving Time

Some locations change their clocks during the year.

For example, Melbourne uses daylight saving during part of the year.

The application uses the timezone information to determine the correct UTC conversion for the selected date.

It also detects local times that do not actually exist because of a daylight-saving clock change.

---

# How This Relates to Real Planetary Movement

The important thing is that the application is based on the **actual calculated movement of the selected body**.

Conceptually, it works like this:

```text
Starting date/time
        ↓
Where is the body?
        ↓
Start longitude
        ↓
Move forward through time
        ↓
Calculate the body's position repeatedly
        ↓
Accumulate its actual movement
        ↓
Current progression
        ↓
Find the next requested progression milestone
        ↓
Find the date/time when it reaches that milestone
```

For example, suppose the Sun starts at:

```text
9° Capricorn
```

The Sun continues moving through the zodiac.

Eventually it passes:

```text
9° Aquarius
9° Pisces
9° Aries
9° Taurus
...
```

After one complete 360° trip, it comes back to approximately:

```text
9° Capricorn
```

But the application's **progression** has increased by 360°.

After two trips:

```text
Progression = 720°
```

The important distinction is therefore:

```text
REAL ASTRONOMICAL MOVEMENT
        ↓
Swiss Ephemeris calculates positions
        ↓
Application measures the movement
        ↓
Movement is accumulated as progression
        ↓
Application finds requested progression milestones
```

So the application is not moving the planets artificially.

It is taking their calculated astronomical positions over time and measuring how far they have actually moved through the zodiac.
