import io
import urllib.request
import zipfile

URL_WWW_CMS_GOV = "www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads"
URL_DOWNLOADS_CMS_GOV = "downloads.cms.gov/files"

SYNPUF_FILES = [
    [URL_WWW_CMS_GOV,       "DE1_0_2008_Beneficiary_Summary_File_Sample_~~.zip"],
    [URL_DOWNLOADS_CMS_GOV, "DE1_0_2008_to_2010_Carrier_Claims_Sample_~~A.zip"],
    [URL_DOWNLOADS_CMS_GOV, "DE1_0_2008_to_2010_Carrier_Claims_Sample_~~B.zip"],
    [URL_WWW_CMS_GOV,       "DE1_0_2008_to_2010_Inpatient_Claims_Sample_~~.zip"],
    [URL_WWW_CMS_GOV,       "DE1_0_2008_to_2010_Outpatient_Claims_Sample_~~.zip"],
    [URL_DOWNLOADS_CMS_GOV, "DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_~~.zip"],
    [URL_WWW_CMS_GOV,       "DE1_0_2009_Beneficiary_Summary_File_Sample_~~.zip"],
    [URL_WWW_CMS_GOV,       "DE1_0_2010_Beneficiary_Summary_File_Sample_~~.zip"],
]
# Beneficiary years and Carrier parts both stage as separate raw files,
# uncombined — FileControl.py (the OHDSI ETL) builds the combined
# versions itself, on demand, when it actually runs.


def build_file_url(base_url, sp_file, sample_number):
    sp_file = sp_file.replace("~~", str(sample_number))
    if sp_file == "DE1_0_2008_to_2010_Carrier_Claims_Sample_11A.zip":
        sp_file = "DE1_0_2008_to_2010_Carrier_Claims_Sample_11A.csv.zip"
    if base_url == URL_DOWNLOADS_CMS_GOV:
        file_url = f"http://{base_url}/{sp_file}"
    else:
        file_url = f"https://{base_url}/{sp_file}"
    if sp_file == "DE1_0_2010_Beneficiary_Summary_File_Sample_1.zip":
        file_url = "https://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/SynPUFs/Downloads/DE1_0_2010_Beneficiary_Summary_File_Sample_20.zip"
    if ".csv.zip" in sp_file:
        sp_file = sp_file.replace(".csv.zip", ".zip")
    return file_url, sp_file


def run(session, sample_number, schema_name, stage_name):
    files_staged = 0

    for base_url, sp_file in SYNPUF_FILES:
        file_url, sp_file = build_file_url(base_url, sp_file, sample_number)

        with urllib.request.urlopen(file_url) as response:
            zip_bytes = response.read()

        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        for name in zf.namelist():
            data = zf.read(name)
            clean_name = name.replace(" - Copy.csv", ".csv")

            stage_location = f"@{schema_name}.{stage_name}/DE_{sample_number}/{clean_name}"
            session.file.put_stream(io.BytesIO(data), stage_location, auto_compress=False, overwrite=False)
            files_staged += 1

    return f"Sample {sample_number}: staged {files_staged} files"