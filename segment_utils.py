from pathlib import Path
from string import Template
from datetime import datetime
from HL7_utils import *


TEMPLATE_BASE = str(Path("hl7_templates"))
MSH_TEMPLATE = "msh.txt"
OBX_TEMPLATE = "obx.txt"
ORC_TEMPLATE = "orc.txt"
PID_TEMPLATE = "pid.txt"
RXA_TEMPLATE = "rxa.txt"
RXR_TEMPLATE = "rxr.txt"


def loadFileTemplate(fileName):
    with open(TEMPLATE_BASE + "/" + fileName, "r") as file:
        return file.read()


def imprintTemplate(template_name, value_dict):
    sectionTemplate = loadFileTemplate(template_name)
    hl7Section = Template(sectionTemplate).substitute(value_dict)
    return hl7Section


def find_login_id(instance):
    if instance == "MDC":
        return "MGW36685"
    if instance == "FAMU":
        return "BCJ72636"
    if instance == "Amazon":
        return "MGW36685"
    if instance == "FIU":
        return "RRN66875"
    if instance == "NomiCare":
        return "MGW36685"


def find_site_id(instance):
    if instance == "MDC":
        return "7000"
    if instance == "FAMU":
        return "8000"
    if instance == "Amazon":
        return "7000"
    if instance == "NomiCare":
        return "7000"


def find_site_description(instance):
    if instance == "MDC":
        return "Nomi Health, Inc"
    if instance == "FAMU":
        return "FLORIDA A&M UNIVERSITY SHS"
    if instance == "Amazon":
        return "Nomi Health, Inc"
    if instance == "NomiCare":
        return "Nomi Health, Inc"


def find_org_name(instance):
    if instance == "MDC":
        return "Nomi Health, Inc"
    if instance == "FAMU":
        return "FLORIDA A&M UNIVERSITY SHS"
    if instance == "Amazon":
        return "Nomi Health, Inc"
    if instance == "NomiCare":
        return "Nomi Health, Inc"


# Generates a message header block by imprinting values from the data frame into a string
# template that is loaded from the file system
def createMSHBlock(msh_dict):
    return imprintTemplate(MSH_TEMPLATE, msh_dict)


# Generates a common order block by imprinting values from the data frame into a string
# template that is loaded from the file system
def createORCBlock(message_control_id):
    orc_dict = dict()
    orc_dict["message_control_id"] = message_control_id
    return imprintTemplate(ORC_TEMPLATE, orc_dict)


# Generates a patient identification block by imprinting values from the data frame into a string
# template that is loaded from the file system
def createPIDBlock(dataRow):
    pid_dict = dict()
    pid_dict["patient_id"] = dataRow["Patient ID"]
    if len(pid_dict["patient_id"]) > 20:
        pid_dict["patient_id"] = pid_dict["patient_id"][0:20]

    pid_dict["last_name"] = hl7StringRead(dataRow["Last Name"])
    pid_dict["first_name"] = hl7StringRead(dataRow["First Name"])

    date_time_string = dataRow["DOB"]
    timestamp = datetime.strptime(date_time_string, "%m/%d/%Y")
    future = datetime.today() + relativedelta(years=1)
    if timestamp >= future:
        timestamp = timestamp.replace(year=timestamp.year - 100)
    pid_dict["patient_dob"] = timestamp.strftime("%Y%m%d")

    pid_dict["patient_gender"] = dataRow["Gender"]
    pid_dict["patient_race"] = convertPatientRace(dataRow["Race"])

    pid_dict["patient_address_1"] = dataRow["Street Address"]
    pid_dict["patient_city"] = hl7StringRead(dataRow["City"])
    pid_dict["state"] = dataRow["State"]
    pid_dict["zip"] = dataRow["Zip Code"]

    pid_dict["phone"] = convertPhoneNumberToHL7(hl7StringRead(dataRow["Phone"]))
    pid_dict["patient_ethinicity"] = convertPatientEthnicity(dataRow["Ethnicity"])
    return imprintTemplate(PID_TEMPLATE, pid_dict)


# Generates a vaccine administratrion block by imprinting values from the data frame into a string
# template that is loaded from the file system
def createRXRBlock(dataRow):
    rxr_dict = dict()
    rxr_dict["route"] = dataRow["Route"]
    rxr_dict["administration_site"] = dataRow["Site"]
    return imprintTemplate(RXR_TEMPLATE, rxr_dict)


def createRXABlock(datarow):
    rxa_dict = dict()
    instance = datarow["Instance"]
    vax_date_string = datarow["Vaccine Administered Date"]
    timestamp = datetime.strptime(vax_date_string, "%m/%d/%Y")
    rxa_dict["procedure_date"] = timestamp.strftime("%Y%m%d")
    rxa_dict["cvx_code"] = datarow["CVX_Code"]
    rxa_dict["Vaccine"] = datarow["Vaccine"]
    rxa_dict["site_id"] = find_site_id(instance)
    rxa_dict["site_description"] = find_site_description(instance)
    rxa_dict["lot_Number"] = datarow["Lot"]
    exp_date_string = datarow["Vaccine Expiration Date"]
    timestamp = datetime.strptime(exp_date_string, "%m/%d/%Y")
    rxa_dict["Vaccine_Expiration"] = timestamp.strftime("%Y%m%d")
    rxa_dict["mfg_code"] = datarow["Manufacturer"]
    rxa_dict["vax_manufacturer"] = datarow["vax_manufacturer"]
    return imprintTemplate(RXA_TEMPLATE, rxa_dict)


# Generates three observation segments by impriting values from the data frame into a string
# template that is loaded from the file system
def createOBXBlock(dataRow):
    obx_dict = dict()
    date_string = dataRow["Vaccine Administered Date"]
    timestamp = datetime.strptime(date_string, "%m/%d/%Y")
    obx_dict["vaccine_date"] = timestamp.strftime("%Y%m%d")
    if dataRow["Manufacturer"] == "BN":
        obx_dict["obx_code"] = "FLSHOTS084"
        obx_dict["obx_status"] = "Unknown/Unspecified"
    else:
        obx_dict["obx_code"] = "FLSHOTS071"
        obx_dict["obx_status"] = "Privately insured"
    return imprintTemplate(OBX_TEMPLATE, obx_dict)
