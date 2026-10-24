"""Nepali (Bikram Sambat) dates to English (Gregorian) dates. Plain code, no AI.

The AI only works out *what* date someone said ("२०२१ साउन १५"); turning a BS date
into an AD date is exact arithmetic, so it's done here with nepali-datetime.
"""
from __future__ import annotations

import datetime as dt

import nepali_datetime as nd

BS_MONTHS_NE = ["बैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज", "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत"]
AD_MONTHS_NE = ["जनवरी", "फेब्रुअरी", "मार्च", "अप्रिल", "मे", "जुन", "जुलाई", "अगस्ट", "सेप्टेम्बर", "अक्टोबर",
                "नोभेम्बर", "डिसेम्बर"]
NE_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
ASCII_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


class BadDate(ValueError):
    pass


def bs_days_in_month(year: int, month: int) -> int:
    if not nd.MINYEAR <= year <= nd.MAXYEAR or not 1 <= month <= 12:
        raise BadDate(f"BS {year}-{month} is outside the supported calendar")
    return nd._days_in_month(year, month)


def bs_to_ad(year: int, month: int, day: int) -> dt.date:
    if day < 1 or day > bs_days_in_month(year, month):
        raise BadDate(f"{BS_MONTHS_NE[month - 1]} {year} has no day {day}")
    return nd.date(year, month, day).to_datetime_date()


def ad_to_bs(date: dt.date) -> tuple[int, int, int]:
    b = nd.date.from_datetime_date(date)
    return b.year, b.month, b.day


def to_date(calendar: str, year: int, month: int, day: int) -> dt.date:
    if calendar.upper() == "BS":
        return bs_to_ad(year, month, day)
    try:
        return dt.date(year, month, day)
    except ValueError as exc:
        raise BadDate(str(exc)) from exc


def format_for_form(date: dt.date, fmt: str = "MM/DD/YYYY") -> str:
    return (fmt.replace("YYYY", f"{date.year:04d}").replace("MM", f"{date.month:02d}")
            .replace("DD", f"{date.day:02d}"))


def describe_ne(date: dt.date, calendar: str) -> str:
    """How the patient sees their date, in the calendar they gave it in."""
    if calendar.upper() == "BS":
        y, m, d = ad_to_bs(date)
        return f"{str(y).translate(NE_DIGITS)} {BS_MONTHS_NE[m - 1]} {str(d).translate(NE_DIGITS)}"
    return f"{str(date.year).translate(NE_DIGITS)} {AD_MONTHS_NE[date.month - 1]} {str(date.day).translate(NE_DIGITS)}"


def describe_en(date: dt.date) -> str:
    return date.strftime("%B %-d, %Y")
