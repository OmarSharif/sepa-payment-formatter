from lxml import etree
import os


def validate_schema(xml_string: str) -> dict:
    """
    Validates a pain.001.001.09 XML string against the official ISO 20022 XSD schema.
    
    Returns a dict with:
        - is_valid: bool
        - errors: list of error messages (empty if valid)
    """
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "schemas",
        "pain.001.001.09.xsd"
    )

    try:
        # load the XSD schema file
        with open(schema_path, "rb") as f:
            schema_doc = etree.parse(f)
        schema = etree.XMLSchema(schema_doc)
    except Exception as e:
        return {
            "is_valid": False,
            "errors": [f"Failed to load schema: {str(e)}"]
        }

    try:
        # parse the XML string
        xml_doc = etree.fromstring(xml_string.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        return {
            "is_valid": False,
            "errors": [f"Invalid XML syntax: {str(e)}"]
        }

    # validate against schema
    is_valid = schema.validate(xml_doc)
    errors = [str(error) for error in schema.error_log]

    return {
        "is_valid": is_valid,
        "errors": errors
    }


if __name__ == "__main__":
    # quick test with a minimal valid pain.001.001.09 XML
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
    <CstmrCdtTrfInitn>
        <GrpHdr>
            <MsgId>TEST-001</MsgId>
            <CreDtTm>2026-04-01T10:00:00</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>1000.00</CtrlSum>
            <InitgPty>
                <Nm>Test Corporation</Nm>
            </InitgPty>
        </GrpHdr>
        <PmtInf>
            <PmtInfId>PMTINF-001</PmtInfId>
            <PmtMtd>TRF</PmtMtd>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>1000.00</CtrlSum>
            <PmtTpInf>
                <SvcLvl>
                    <Cd>SEPA</Cd>
                </SvcLvl>
            </PmtTpInf>
            <ReqdExctnDt>
                <Dt>2026-04-02</Dt>
            </ReqdExctnDt>
            <Dbtr>
                <Nm>Test Corporation</Nm>
            </Dbtr>
            <DbtrAcct>
                <Id>
                    <IBAN>DE89370400440532013000</IBAN>
                </Id>
            </DbtrAcct>
            <DbtrAgt>
                <FinInstnId>
                    <BICFI>DEUTDEDB</BICFI>
                </FinInstnId>
            </DbtrAgt>
            <CdtTrfTxInf>
                <PmtId>
                    <EndToEndId>E2E-001</EndToEndId>
                </PmtId>
                <Amt>
                    <InstdAmt Ccy="EUR">1000.00</InstdAmt>
                </Amt>
                <CdtrAgt>
                    <FinInstnId>
                        <BICFI>BNPAFRPP</BICFI>
                    </FinInstnId>
                </CdtrAgt>
                <Cdtr>
                    <Nm>Supplier GmbH</Nm>
                </Cdtr>
                <CdtrAcct>
                    <Id>
                        <IBAN>FR7630006000011234567890189</IBAN>
                    </Id>
                </CdtrAcct>
            </CdtTrfTxInf>
        </PmtInf>
    </CstmrCdtTrfInitn>
</Document>"""

    result = validate_schema(test_xml)
    
    if result["is_valid"]:
        print("✓ XML is valid against pain.001.001.09 schema")
    else:
        print("✗ XML is invalid")
        for error in result["errors"]:
            print(f"  - {error}")

# test with invalid XML - missing required fields
    invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
    <CstmrCdtTrfInitn>
        <GrpHdr>
            <MsgId>TEST-002</MsgId>
            <CreDtTm>2026-04-01T10:00:00</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>1000.00</CtrlSum>
        </GrpHdr>
    </CstmrCdtTrfInitn>
</Document>"""

    print("\nTesting invalid XML...")
    result2 = validate_schema(invalid_xml)

    if result2["is_valid"]:
        print("✓ XML is valid")
    else:
        print("✗ XML is invalid — errors found:")
        for error in result2["errors"]:
            print(f"  - {error}")