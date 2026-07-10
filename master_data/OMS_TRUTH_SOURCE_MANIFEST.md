# OMS Truth Source Manifest

Version: 1.0
Status: Production Metadata
Owner: 石磊
Last Update: 2026-07-10

---

## Storage Policy

`OMS_TRUTH_SOURCE/` remains ignored by Git.

Real production data must not be uploaded to GitHub, including:

- customer identity data
- contract data
- financial transaction data
- room status production data
- generated production JSON files
- original production Excel files

GitHub may store only:

- Adapter code
- Schema
- data dictionary
- blank Excel templates
- this manifest
- validation rules
- desensitized test samples
- import reports

---

## Local Truth Source Files

| Source | Local Path | Domain | Records |
|---|---|---|---:|
| Sales | `OMS_TRUTH_SOURCE/sales.json` | Sales / Contract / Payment metrics | 224 |
| Finance | `OMS_TRUTH_SOURCE/finance.json` | Finance / Payment / Expense / Settlement | 1278 events / 11 settlements |
| Room | `OMS_TRUTH_SOURCE/room.json` | Room / Room Status | 42 |
| Stay | `OMS_TRUTH_SOURCE/stay.json` | Stay / Stay Plan | 172 |
| Customer | `OMS_TRUTH_SOURCE/customer.json` | Customer | 148 |
| Contract | `OMS_TRUTH_SOURCE/contract.json` | Contract | 148 |

---

## Boundary Rules

| File | Allowed Content | Forbidden Content |
|---|---|---|
| `sales.json` | sales facts, sales amount, received amount, unpaid amount | room status, stay lifecycle, customer identity master |
| `finance.json` | financial events, receivable, payable, income, expense | sales pipeline, room status |
| `room.json` | room list, room status, room status warnings | customer records, contract records, stay plans |
| `stay.json` | current stay markers, planned stays, check-in status | room inventory, contract amount master |
| `customer.json` | customer identity and contact fields | room status, finance events |
| `contract.json` | contract facts, package, contract amount, sales owner | room status, finance ledger |

---

## Local Backup

Latest controlled local backup:

`D:\凰家母婴空间\OMS_TRUTH_SOURCE_BACKUP\20260710_154049`

Backup includes:

- original four Excel files
- generated JSON truth sources
- verification JSON files
- manifest JSON

---

## Runtime Chain

```text
Excel
-> OMS_TRUTH_SOURCE/*.json
-> Production Adapter
-> Domain
-> API Contract
-> Page Contract
-> Metrics
-> AI Context
```

This manifest is metadata only. It is safe for GitHub because it contains counts and rules, not production entity rows.
