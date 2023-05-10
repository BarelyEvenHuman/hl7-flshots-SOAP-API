import boto3
import pandas as pd
import random
import json
import botocore
import os
from zeep import Client, xsd
from datetime import datetime
from segment_utils import *
from aws_lambda_powertools import Logger
from urllib.parse import unquote_plus
from io import StringIO


logger = Logger(service="flshots_hl7")
logger.append_keys(doh="Florida")
logger.append_keys(patientid="")
logger.append_keys(vaccinedate="")
logger.append_keys(file_used="")


wsdl_file = (
    os.environ["LAMBDA_TASK_ROOT"] + "/wsdl-iis-soap-implement-code.FLSHOTS.v3.xml"
)
method_url = "https://www.flshots.com/interop/InterOp.Service.HL7IISMethods.cls"
service_url = "https://www.flshots.com/interop/InterOp.Service.HL7IISMethods.cls"
FLSHOTS_SECRETS = ""


header = xsd.Element(
    "Header",
    xsd.ComplexType(
        [
            xsd.Element(
                "{http://www.w3.org/2003/05/soap-envelope}Action", xsd.String()
            ),
            xsd.Element("{http://www.w3.org/2003/05/soap-envelope}To", xsd.String()),
        ]
    ),
)


def hl7_to_flshots(wsdl_file, doc_string, header, secrets):
    """Sends HL7 message to FL Shots via SOAP api."""
    for _ in range(5):  # basic retry logic
        try:
            header_value = header(Action=method_url, To=service_url)
            client = Client(wsdl=wsdl_file)
            response = client.service.submitSingleMessage(
                username=secrets["username"],
                password=secrets["password"],
                hl7Message=doc_string,
                _soapheaders=[header_value],
            )
            if response.find("MSA|AA") != -1:
                logger.info("Message Accepted.")
                break
            elif response.find("MSA|AE") != -1:
                err = response.find("ERR")
                warn = response[err:]
                end = warn.find("\n")
                logger.warn(f"Message accepted with warnings. {warn[:end]}")
                break
            elif response.find("MSA|AR") != -1:
                err = response.find("ERR")
                error = response[err:]
                end = error.find("\n")
                logger.error(f"Message Rejected. {error[:end]}")
                break
            else:
                logger.warning(f"Response: {response}. Retry Count: {_}")
            return response
        except Exception as e:
            logger.error(f"Failed to connect to FL Shots. Retry Count: {_} {e}")


def get_secrets(sm):
    """Retrieves secrets for Snowflake credentials."""
    return json.loads(sm.get_secret_value(SecretId=FLSHOTS_SECRETS)["SecretString"])


def fetch_mdc_data(boto3, event):
    """returns data from most recent file, triggered by s3."""
    try:
        upload_bucket = "nomi-prod-ue1-vaccines-hl7-writeback"
        object_key = unquote_plus(
            event["Records"][0]["s3"]["object"]["key"], encoding="utf-8"
        )
        logger.append_keys(file_used=object_key)
        s3 = boto3.client(
            "s3",
            "us-east-1",
            config=botocore.config.Config(s3={"addressing_style": "path"}),
        )
        csv_obj = s3.get_object(Bucket=upload_bucket, Key=object_key)
        body = csv_obj["Body"]
        csv_string = body.read().decode("utf-8")
        df = pd.read_csv(StringIO(csv_string))
        return df
    except Exception as e:
        logger.error(f"Could not pull data from s3. {e}")


def create_message_control_id():
    message_control_id: str = (
        "117"
        + str(random.randrange(10000, 99999))
        + "."
        + str(random.randrange(100, 999))
    )
    logger.info("control_number: " + message_control_id)
    return message_control_id


def msh_segment(instance, message_control_id):
    """Assigns values to the MSH segment."""
    msh_dict = dict()
    message_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    msh_dict["message_time_stamp"] = message_timestamp
    msh_dict["message_control_id"] = message_control_id
    msh_dict["login_id"] = find_login_id(instance)
    msh_dict["org_name"] = find_org_name(instance)
    MSHSegment = createMSHBlock(msh_dict)
    return MSHSegment


def HL7DocumentToFile(hl7_string, patient_id, index, vaxdate):
    """Creates hl7 file and uploads to s3."""
    try:
        document_string = "".join(hl7_string)
        hl7_file_name = f"NomiHealth-{str(patient_id)}-{str(index)}.hl7"
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket="nomi-prod-ue1-vaccines-hl7-writeback",
            Key="flshots-hl7-messages/" + hl7_file_name,
            Body=bytes(document_string, encoding="utf-8"),
        )
        logger.info(f"Wrote file {hl7_file_name} to s3 bucket.")
        return document_string
    except Exception as e:
        logger.error(
            f"Unable to submit HL7 file to s3. patient_id: {patient_id}, vaccine date: {vaxdate} {e}."
        )


def lambda_handler(event, context):
    logger.info("FLShots Lambda Triggered.")
    df = fetch_mdc_data(boto3, event)
    logger.info(f"Records to process: {len(df)}")
    sm = boto3.client("secretsmanager")
    secrets = get_secrets(sm)
    for index in range(len(df)):
        try:
            patientid = df["Patient ID"][index]
            vaxdate = df["Vaccine Administered Date"][index]
            logger.append_keys(patientid=patientid)
            logger.append_keys(vaccinedate=vaxdate)
            message_control_id = create_message_control_id()
            instance = df["Instance"][index]
            patient_id = df["Patient ID"][index]
            record = df.iloc[index]
            msh = msh_segment(instance, message_control_id)
            pid = createPIDBlock(record)
            orc = createORCBlock(message_control_id)
            rxa = createRXABlock(record)
            rxr = createRXRBlock(record)
            obx = createOBXBlock(record)
            hl7_string = [x for x in [msh, pid, orc, rxa, rxr, obx]]
        except Exception as e:
            logger.error(
                f"Message generation failed. Patient ID: {patient_id}, Vaccine Date: {vaxdate} {e}."
            )
        doc_string = HL7DocumentToFile(hl7_string, patient_id, index, vaxdate)
        hl7_to_flshots(wsdl_file, doc_string, header, secrets)
    logger.info("Function Complete.")
