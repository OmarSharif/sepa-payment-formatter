# SEPA Payment Formatter

An AI agent that validates and corrects SEPA payment files before
they are sent to a bank or payment provider.

## Background

In the payments world there are a lot of different rules and formats
to follow depending on your bank or payment provider. Payment files
need to conform to a specific schema and meet bank-specific business
rules before a bank will accept them. When files are rejected it
causes payment delays, recall fees, and manual investigation by
treasury teams.

Creating custom file transformations for each bank is time consuming.
The idea behind this project is that you can feed Claude the rules for
any bank and have it validate and correct payment files automatically.
This can lower bank rejection rates and speed up the process of
onboarding new banks without writing custom code for each one.

This is a prototype demonstrating what an AI validation layer could
look like as an add-on to existing payment platforms.

## How It Works

The agent runs four tools in sequence and makes decisions about
what to fix automatically versus what to flag for human review.

Raw payment file
↓
Tool 1: Schema Validation
Validates the XML against the official ISO 20022 pain.001.001.09
EPC schema. Catches structural errors like missing fields, wrong
formats, and invalid element order.
↓
Tool 2: IBAN Validation
Calls the ibanapi.com REST API to verify each IBAN is real and
reachable. Returns bank name, BIC code, and confirms whether
the country is a SEPA member.
↓
Tool 3: Bank Rules Validation
Validates the payment against bank-specific business rules sourced
from the EPC SEPA Credit Transfer Implementation Guidelines 2025.
Currently covers Deutsche Bank, BNP Paribas, ABN AMRO, and
Commerzbank. Three rules per bank:

1. Payment method must be TRF for SEPA Credit Transfers
2. Amount must have exactly 2 decimal places
3. Receiver IBAN country should match bank home country

↓
Tool 4: XML Fixer (if errors found)
Attempts to correct the payment file based on errors found.
Fixes deterministic errors automatically. For ambiguous errors
Claude uses judgment. For example a payment method of "trf"
gets fixed to TRF, but "cheque" gets flagged for human review
because that is a fundamentally different payment type. The
agent will not make changes that are risky or unclear.
↓
Revalidation
After fixing, the agent revalidates the schema to confirm
the corrections worked.
↓
Final Report
A complete summary of what was found, what was fixed,
and what requires human attention.

## Schema

Uses the official ISO 20022 pain.001.001.09 XSD schema sourced
from iso20022.org. This is the version currently required by
Deutsche Bank and other major European banks for SEPA payments.

## Bank Rules

Bank rules are sourced from the EPC SEPA Credit Transfer
Customer-to-PSP Implementation Guidelines 2025, the official
public document published by the European Payments Council
that all SEPA banks must follow.

The current rule library covers 5 banks and implements a
representative subset of rules as a proof of concept. Each bank
publishes a full implementation guide with many additional rules.
The roadmap section describes how this would scale using RAG.

## Setup
```bash
git clone https://github.com/OmarSharif/sepa-payment-formatter.git
cd sepa-payment-formatter

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

ANTHROPIC_API_KEY=your_anthropic_key
IBANAPI_KEY=your_ibanapi_key

You can get a free ibanapi.com key at ibanapi.com.

## Running the Agent
```bash
python3 agent.py
```

The test payment data is hardcoded in `agent.py` for now.
You can update the `test_xml` and `test_payment_data` variables
to validate your own payment files.

## Limitations

- Bank rules are manually maintained. Someone has to read each
  bank's implementation guide and encode the rules in bank_rules.py
- Currently covers 5 banks with a subset of rules per bank
- No live bank submission. Deutsche Bank's API requires corporate
  credentials for sandbox access so final bank acceptance is not
  verified in this version
- No UI. This is a Python CLI tool

## Evaluation (In Progress)

An eval harness is planned to measure how well the agent performs
across different payment scenarios. Test cases will cover:

- Valid payments the agent should approve
- Fixable errors the agent should correct automatically
- Ambiguous errors the agent should flag for human review
- Multiple errors in a single file

The eval will score detection accuracy, fix accuracy, and
escalation accuracy separately.

## Roadmap

- [ ] Eval harness with labeled test cases
- [ ] RAG pipeline to ingest bank implementation PDFs so Claude
      can retrieve bank rules dynamically instead of manually
      maintained code. This would allow rapid onboarding of
      new banks without writing custom rules for each one
- [ ] Expanded bank library beyond current 5 banks
- [ ] Live bank API integration for final submission verification
- [ ] REST API wrapper so other systems can call this as a service

## Related

Built on concepts from payment-classifier, a separate project
that evaluates Claude's ability to classify ISO 20022 payment
errors across a labeled dataset.

