# OMS Master Data

This directory defines the OMS master-data layer.

It does not duplicate official organization data.

Canonical sources:

- `D:\凰家大脑\brain\03_organization\oms\OMS_组织主数据.md`
- `D:\凰家大脑\brain\03_organization\oms\OMS_飞书身份映射.md`

OMS modules must read through `oms_v1.master_data.OMSMasterData`.

Do not maintain employee lists, Feishu user IDs, approval identities, permission owners, AI Agent owners, or notification targets in module-local constants.
