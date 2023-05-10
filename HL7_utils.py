from datetime import datetime
import phonenumbers
from dateutil.relativedelta import relativedelta


# substitutes a caret if the string is blank from the input stream
def hl7StringRead(some_string):
    try:
        if isinstance(some_string, str):
            if not some_string:
                return "^"
            else:
                return some_string
        else:
            return ""
    except Exception:
        return ""


# returns the key in a string dictionary if the values match
def searchDictonary(a_dictionary, some_value):
    for key, value in a_dictionary.items():
        # for v in value:
        if some_value.lower() in value.lower():
            return key


def convertStringDateToHL7(inputDate):
    try:
        if isinstance(inputDate, str):
            future = datetime.today() + relativedelta(years=1)
            timestamp = datetime.strptime(inputDate, "%m/%d/%y")
            if future <= timestamp:  # must be in the past
                timestamp = timestamp.replace(year=timestamp.year - 100)

            return timestamp.strftime("%Y%m%d%H")
        else:
            return ""
    except ValueError:
        return ""


def convertStringDateTimeToHL7(inputDate):
    try:
        if isinstance(inputDate, str):
            future = datetime.today() + relativedelta(years=1)
            timestamp = datetime.strptime(inputDate, "%m/%d/%y %H:%M")
            if future <= timestamp:  # must be in the past
                timestamp = timestamp.replace(year=timestamp.year - 100)

            return timestamp.strftime("%Y%m%d%H%M%S")
        else:
            return ""
    except ValueError:
        return ""


def convertPhoneNumberToHL7(inputPhoneNumber):
    try:
        if isinstance(inputPhoneNumber, str):
            phone_number = phonenumbers.parse(inputPhoneNumber, "US")
            digits = str(phone_number.national_number)
            formatted = digits[:3] + "^" + digits[-7:]
            if formatted == "0^0":
                return ""
            else:
                return formatted
        else:
            return ""
    except Exception:
        return ""


def convertPatientRace(race_string):
    raw_string = hl7StringRead(race_string)
    if raw_string.lower().startswith("w"):
        return "2106-3^White"
    if raw_string.lower().startswith("asian"):
        return "2028-9^Asian"
    if raw_string.lower().startswith("black"):
        return "2054-5^Black"
    if raw_string.lower().startswith("africa"):
        return "2054-5^African_American"
    if "alaska" in raw_string.lower():
        return "1002-5^alaska_native"
    if raw_string.lower().startswith("other"):
        return "2131-1^Other_Race"
    if "hawaii" in raw_string.lower():
        return "2076-8^native_hawaiian"
    if "pacific" in raw_string.lower():
        return "2076-8^pacific_islander"
    return "2131-1^Other_Race"


def convertPatientEthnicity(ethnicity_string):
    raw_string = hl7StringRead(ethnicity_string)
    if raw_string.lower().startswith("not"):
        return "N^Not Hispanic or Latino"
    if raw_string.lower().startswith("hispanic") or raw_string.lower().startswith(
        "latino"
    ):
        return "H^Hispanic or Latino"
    return "U^Unknown"
