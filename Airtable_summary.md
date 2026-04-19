# Sterilization_Main Database Schema Documentation for Bot Integration

## Executive Summary

This document provides a comprehensive technical description of the **sterilization_main** database schema, designed to facilitate the integration of a requestors' bot with the existing forms and data management system. The database serves as the backbone for managing cat sterilization requests, fostering operations, medical care tracking, inventory management, and international cat travel preparation. Understanding the structure, relationships, and data flows within this system is essential for developing a bot that can seamlessly interact with requestors, collect information, and populate the appropriate records.

---

## Database Overview

The **sterilization_main** database comprises **13 interconnected tables** that collectively manage the entire lifecycle of sterilization requests—from initial submission through medical care, fostering, and eventual release or adoption. The system supports multilingual operations (Russian, English, Georgian) and tracks detailed information about requestors, cats, medical treatments, inventory, volunteer schedules, and international travel preparation.

**Total Records Across All Tables:**

- **sterilization_request**: 2,537 records
- **cat_flat_fostering**: 1,467 records
- **inventory**: 38 records
- **MedicalCare**: 482 records
- **TreatmentDays**: 2,240 records
- **shedule**: 929 records (synced table)
- **в наличии** (medications in stock): 189 records (synced table)
- **в наличии 2** (medications with expiration): 189 records (synced table)
- **cat_travel_prep**: 20 records
- **cat_travel_contacts**: 5 records
- **intake_release**: 1 record
- ***intake*release**: 3 records
- **частота использования лекарств**: 3 records

---

## Core Tables for Bot Integration

### 1. sterilization_request (Primary Request Table)

This is the **central table** for bot integration, containing all sterilization request data submitted by requestors. The bot should primarily write to this table when collecting new requests.

#### Key Fields for Bot Input


| Field Name            | Type             | Description                                      | Bot Integration Notes                                                                                                                     |
| --------------------- | ---------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **requestor_name**    | Single line text | Name of the person submitting the request        | Required field for identification                                                                                                         |
| **requestor_contact** | Long text        | Full contact information block                   | Legacy field containing formatted contact details                                                                                         |
| **phone**             | Phone number     | Requestor's phone number                         | Primary contact method                                                                                                                    |
| **telegram**          | Single line text | Telegram username                                | Important for communication                                                                                                               |
| **whatsapp**          | Single line text | WhatsApp number                                  | Alternative contact                                                                                                                       |
| **viber**             | Single line text | Viber number                                     | Alternative contact                                                                                                                       |
| **email**             | Single line text | Email address                                    | For automated notifications                                                                                                               |
| **instagram**         | Single line text | Instagram handle                                 | Social media contact                                                                                                                      |
| **messengers**        | Multiple select  | Preferred messengers (telegram, whatsapp, viber) | Bot should collect this preference                                                                                                        |
| **address**           | Single line text | Physical address for pickup/delivery             | Required for logistics                                                                                                                    |
| **geo_location**      | Single line text | Google Maps link                                 | Helps with location verification                                                                                                          |
| **district**          | Single select    | City district                                    | Options include: Сабуртало/Saburtalo/საბურთალო, Ваке/Vake/ვაკე, Глдани/Gldani/გლდანი, Дидубе/Didube/დიდუბე, Исани/Isani/ისანი, and others |


#### Cat Information Fields


| Field Name              | Type          | Description                 | Options/Notes                                                                                                                                       |
| ----------------------- | ------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **sex**                 | Single select | Cat's sex                   | Кошка/Female/ძუ (female), Кот/Male/ხვადი (male)                                                                                                     |
| **cat_type**            | Single select | Domestic or street cat      | Домашняя/house cat/სახლის კატა, Уличная/street cat/ქუჩის კატა                                                                                       |
| **wild_or_tame**        | Single select | Cat's temperament           | Дикая/Wild/ველური, Ручная/Tame/შინაური, Пугливая/Fearful/მშიშარა                                                                                    |
| **health**              | Single select | Health status               | Здорова/Healthy/ჯანმრთელია, Проблемы со здоровьем/Health problems/აქვს ჯანმრთელობის პრობლემები, Не могу определить/Can't determine/ვერ განვსაზღვრავ |
| **health_notes**        | Long text     | Detailed health information | Free text for health concerns                                                                                                                       |
| **is_pregnant**         | Single select | Pregnancy status            | Да/Yes/დიახ, Нет/No/არა, Нет уверенности/Not sure/არ ვარ დარწმუნებული                                                                               |
| **pregnant_notes**      | Long text     | Pregnancy details           | Additional pregnancy information                                                                                                                    |
| **is_deflead**          | Single select | Flea treatment status       | Да/Yes/დიახ, Нет/No/არა                                                                                                                             |
| **is_vaccinated**       | Single select | Vaccination status          | Да/Yes/დიახ, Нет/No/არა                                                                                                                             |
| **cat_picture**         | Attachment    | Photo of the cat            | Important for identification                                                                                                                        |
| **Примерный вес кошки** | Rating (1-7)  | Estimated cat weight        | 1 = kitten (~1kg), 2-3 = thin street cat, 3.5-4+ = large cat                                                                                        |


#### Service Preferences


| Field Name            | Type          | Description                | Options                                                                                                                                                                 |
| --------------------- | ------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **clinic**            | Single select | Preferred clinic           | Без разницы/No preference, Aibolit+ (Rustavi), ZooCity (Saburtalo), Lucky Paw, Zoofamily, Vet House, Bionika (Isani), Didi Dog (Didi Digomi), New Vet (Varketili), Киви |
| **catch_type**        | Single select | Catching assistance needed | Поймаем сами/We will catch ourselves, Нужна помощь с поимкой/Need help catching                                                                                         |
| **needs_foster_care** | Single select | Foster care requirement    | Да, оставлю у себя/Yes, I can keep, Нет, оставьте кошку в котодоме/No, keep in catflat                                                                                  |
| **need_carrier**      | Checkbox      | Carrier needed             | Boolean                                                                                                                                                                 |
| **return_type**       | Single select | Return method preference   | Заберу самостоятельно/I will pick up, Доставкой за свой счет/Delivery at my expense                                                                                     |


#### Payment Information


| Field Name              | Type          | Description                | Options                                                                                                   |
| ----------------------- | ------------- | -------------------------- | --------------------------------------------------------------------------------------------------------- |
| **payment_choice**      | Single select | General payment preference | Оплачу полностью/I will pay in full, Оплачу частично/I will pay partially, За счет Catebi/Catebi will pay |
| **pay_for_a_streetcat** | Single select | Payment for street cat     | оплачу полную стоимость/full price, могу оплатить только часть/partial                                    |
| **pay_for_a_house_cat** | Single select | Payment for house cat      | оплачу целиком/full price                                                                                 |
| **pay_for_pride**       | Single select | Payment for pride cats     | могу оплатить/can pay, могу оплатить часть/partial, не могу оплатить/cannot pay                           |
| **is_paid**             | Single select | Payment status             | Оплачено полностью/Paid in full, Оплачено частично/Partially paid, Не оплачено/Not paid                   |


#### Vaccination Requests


| Field Name                 | Type          | Description                          |
| -------------------------- | ------------- | ------------------------------------ |
| **complex_req**            | Checkbox      | Complex vaccination requested        |
| **rabies_req**             | Checkbox      | Rabies vaccination requested         |
| **complex_vatebi_vac_req** | Checkbox      | Complex Catebi vaccination requested |
| **vac_payment_type_stray** | Single select | Vaccination payment for strays       |
| **vac_payment_type_house** | Single select | Vaccination payment for house cats   |
| **vac_payment_type_pride** | Single select | Vaccination payment for pride cats   |


#### Administrative Fields


| Field Name       | Type          | Description                                                                                                                                                                                                                                                                                                                      |
| ---------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **id**           | Autonumber    | Unique request identifier (primary key)                                                                                                                                                                                                                                                                                          |
| **created_date** | Date          | Request creation date                                                                                                                                                                                                                                                                                                            |
| **status**       | Single select | Request status: Новая заявка (New), Коммуникация с заявителем (Communication), Стерилизация назначена (Scheduled), Стерилизация перенесена (Rescheduled), На пути в котодом (On the way), Возвращена заявителю (Returned), Стерилизация отменена (Cancelled), принята в кк (Accepted), Заявитель перестал отвечать (No response) |
| **operator**     | Single select | Assigned operator                                                                                                                                                                                                                                                                                                                |
| **steril_date**  | Date          | Scheduled sterilization date                                                                                                                                                                                                                                                                                                     |
| **sterilized**   | Checkbox      | Sterilization completed                                                                                                                                                                                                                                                                                                          |
| **language**     | Single select | Requestor's language                                                                                                                                                                                                                                                                                                             |
| **is_volunteer** | Checkbox      | Requestor is a volunteer                                                                                                                                                                                                                                                                                                         |
| **isHere**       | Checkbox      | Cat is currently at the facility                                                                                                                                                                                                                                                                                                 |
| **notes**        | Long text     | General notes                                                                                                                                                                                                                                                                                                                    |
| **ear-tipping**  | Checkbox      | Ear tipping required                                                                                                                                                                                                                                                                                                             |


#### Computed/Formula Fields (Read-Only for Bot)


| Field Name               | Type    | Description                                                    |
| ------------------------ | ------- | -------------------------------------------------------------- |
| **Contacts**             | Formula | Formatted contact information                                  |
| **Нужно вакцинировать?** | Formula | Vaccination summary with total amount and payment type         |
| **payment_calculated**   | Formula | Calculated payment responsibility                              |
| **sex_calculated**       | Formula | Normalized sex value                                           |
| **pregnancy_calculated** | Formula | Normalized pregnancy status                                    |
| **vac_payment_calc**     | Formula | Calculated vaccination payment (35 for complex, 10 for rabies) |
| **created_year_month**   | Formula | Year-month of creation (YYYY-MM format)                        |


---

### 2. cat_flat_fostering (Cat House Fostering)

This table tracks cats during their stay at the cat flat (котодом). Records are typically created when a cat arrives for sterilization and fostering.

#### Key Fields


| Field Name                   | Type            | Description                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **cat_house_foster_id**      | Autonumber      | Unique fostering record ID (primary key)                                                                                                                                                                                                                                                                                                                                  |
| **request**                  | Linked record   | Link to sterilization_request                                                                                                                                                                                                                                                                                                                                             |
| **status**                   | Single select   | Current status: на пути в кд (on the way), принята в кд (accepted), ожидает стерилизацию (awaiting sterilization), на стерилизации (in sterilization), готова к выписке (ready for release), на сторонней передержке (external foster), передана заявителю (returned to requestor), назначен медуход (medical care assigned), укотовлена (adopted), в клинике (at clinic) |
| **room**                     | Multiple select | Room assignment: K1, K2, Hall, Balcony, cage                                                                                                                                                                                                                                                                                                                              |
| **in_date**                  | Date            | Arrival date                                                                                                                                                                                                                                                                                                                                                              |
| **out_date**                 | Date            | Release date                                                                                                                                                                                                                                                                                                                                                              |
| **images**                   | Attachment      | Photos of the cat                                                                                                                                                                                                                                                                                                                                                         |
| **notes_kk**                 | Long text       | Cat flat notes                                                                                                                                                                                                                                                                                                                                                            |
| **receptionist**             | Single select   | Staff who received the cat                                                                                                                                                                                                                                                                                                                                                |
| **Evil_or_not**              | Single select   | Temperament indicator: 😈 (aggressive), 😱 (scared), 😇 (friendly)                                                                                                                                                                                                                                                                                                        |
| **is_deflead**               | Checkbox        | Flea treatment done at facility                                                                                                                                                                                                                                                                                                                                           |
| **is_vaccinated**            | Checkbox        | Vaccination done at facility                                                                                                                                                                                                                                                                                                                                              |
| **is_dewormed**              | Checkbox        | Deworming done                                                                                                                                                                                                                                                                                                                                                            |
| **med_care**                 | Checkbox        | Medical care required                                                                                                                                                                                                                                                                                                                                                     |
| **carrier_returned**         | Checkbox        | Carrier returned to requestor                                                                                                                                                                                                                                                                                                                                             |
| **cage**                     | Checkbox        | Cat is in a cage                                                                                                                                                                                                                                                                                                                                                          |
| **room_cage**                | Formula         | Combined room and cage status                                                                                                                                                                                                                                                                                                                                             |
| **Duration**                 | Formula         | Days in fostering                                                                                                                                                                                                                                                                                                                                                         |
| **Days Since Sterilization** | Formula         | Days since sterilization procedure                                                                                                                                                                                                                                                                                                                                        |
| **Дата выписки**             | Formula         | Calculated release date (sterilization date + 6 days)                                                                                                                                                                                                                                                                                                                     |
| **isReleased**               | Checkbox        | Cat has been released                                                                                                                                                                                                                                                                                                                                                     |
| **isReady**                  | Checkbox        | Cat is ready for release                                                                                                                                                                                                                                                                                                                                                  |
| **isNew**                    | Checkbox        | New arrival flag                                                                                                                                                                                                                                                                                                                                                          |


#### Lookup Fields from sterilization_request

The table includes numerous lookup fields that pull data from the linked sterilization request, including requestor contact information, cat details, and service preferences.

---

### 3. inventory (Equipment Inventory)

Tracks carriers, cages, and cat traps available for lending to requestors.

#### Key Fields


| Field Name                       | Type             | Description                                                                                                                         |
| -------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Notes**                        | Autonumber       | Inventory item ID (primary key)                                                                                                     |
| **Name**                         | Single line text | Item name/description                                                                                                               |
| **Type**                         | Single select    | Item type: переноска твердая (hard carrier), переноска мягкая (soft carrier), манеж маленький (small playpen), котоловка (cat trap) |
| **Photo**                        | Attachment       | Item photo                                                                                                                          |
| **Condition**                    | Single line text | Item condition                                                                                                                      |
| **sterilization_request**        | Linked record    | Link to request using this item                                                                                                     |
| **Кому отдали если нет заявки?** | Single line text | Who received item if no request linked                                                                                              |
| **free?**                        | Formula          | Availability status: "Available" or "Borrowed"                                                                                      |


---

### 4. MedicalCare (Medical Treatment Assignments)

Manages medical treatment prescriptions for cats in care.

#### Key Fields


| Field Name                        | Type          | Description                                                                 |
| --------------------------------- | ------------- | --------------------------------------------------------------------------- |
| **Cat info**                      | Formula       | Combined cat and treatment info (primary key)                               |
| **Кошка**                         | Linked record | Link to cat_flat_fostering                                                  |
| **Лекарство**                     | Linked record | Link to medication (в наличии table)                                        |
| **Лекарство+срок годности**       | Linked record | Link to medication with expiration (в наличии 2 table)                      |
| **Дата начала приема**            | Date          | Treatment start date                                                        |
| **Дата окончания приема**         | Date          | Treatment end date                                                          |
| **Назначение активно?**           | Checkbox      | Treatment is active                                                         |
| **Коммент (общий)**               | Long text     | General treatment notes                                                     |
| **Тип**                           | Single select | Treatment type: проверка (check), лечение (treatment), внимание (attention) |
| **Дозировка (таблетки, капсулы)** | Number        | Dosage for tablets/capsules                                                 |
| **TreatmentDays**                 | Linked record | Link to daily treatment records                                             |
| **Кол-во дней приема**            | Formula       | Number of treatment days                                                    |
| **Количество к списанию**         | Formula       | Quantity to write off from inventory                                        |


---

### 5. TreatmentDays (Daily Treatment Tracking)

Tracks individual treatment days and completion status.

#### Key Fields


| Field Name             | Type          | Description                                          |
| ---------------------- | ------------- | ---------------------------------------------------- |
| **Name**               | Formula       | Combined cat, medicine, and date (primary key)       |
| **Назначение**         | Linked record | Link to MedicalCare                                  |
| **Дата**               | Date          | Treatment date                                       |
| **Done**               | Checkbox      | Treatment completed                                  |
| **Коммент по лечению** | Long text     | Treatment notes for this day                         |
| **Дежурный**           | Linked record | Link to volunteer on duty (shedule table)            |
| **Лечение**            | Lookup        | Treatment name                                       |
| **Комната**            | Lookup        | Room assignment                                      |
| **duty_key**           | Formula       | Key for matching with schedule (YYYY-MM-DD::medical) |


---

### 6. shedule (Volunteer Schedule) — Synced Table

Contains volunteer duty assignments. This is a **synced table** (read-only from this base).

#### Key Fields


| Field Name           | Type             | Description                                                                       |
| -------------------- | ---------------- | --------------------------------------------------------------------------------- |
| **telegram**         | Single line text | Volunteer's Telegram (primary key)                                                |
| **volunteer**        | Single line text | Volunteer identifier                                                              |
| **name**             | Single line text | Volunteer name                                                                    |
| **date**             | Date             | Duty date                                                                         |
| **telegram_chat_id** | Number           | Telegram chat ID for notifications                                                |
| **type**             | Single select    | Duty type: cleaning, cleaning_catloft, medical, steril_acceptance, steril_release |
| **duty_key**         | Formula          | Key for matching with treatments                                                  |
| **TreatmentDays 3**  | Linked record    | Link to assigned treatments                                                       |


---

### 7. в наличии (Medications in Stock) — Synced Table

Master list of available medications. This is a **synced table** (read-only from this base).

#### Key Fields


| Field Name            | Type             | Description                                                                                                                                                                                             |
| --------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Name**              | Single line text | Medication name (primary key)                                                                                                                                                                           |
| **единица измерения** | Single select    | Unit of measurement: таблетка (tablet), капсула (capsule), флакон (vial), ампула (ampoule), туба (tube), пакет (packet), пипетка (pipette), штука (piece), банка с порошком (powder jar), саше (sachet) |
| **active_substance**  | Single line text | Active ingredient                                                                                                                                                                                       |
| **in stock**          | Number           | Quantity in stock                                                                                                                                                                                       |
| **Расположение**      | Single select    | Storage location: ящик 1-3 (drawer 1-3), ХОЛОДИЛЬНИК (refrigerator), УСПАКОИНЫ, ОТКРЫТАЯ ПОЛКА (open shelf), Черный комод ящик 1-3, Голубой комод ящик 1-2                                              |
| **what_for**          | Single select    | Medication category (antibiotics, pain relief, etc.)                                                                                                                                                    |
| **EXP**               | Date             | Expiration date                                                                                                                                                                                         |
| **EXP Status**        | Long text        | Expiration status                                                                                                                                                                                       |


---

### 8. в наличии 2 (Medications with Expiration) — Synced Table

Extended medication information including batch-level expiration tracking. This is a **synced table** (read-only from this base).

#### Key Fields


| Field Name            | Type             | Description                                                                                          |
| --------------------- | ---------------- | ---------------------------------------------------------------------------------------------------- |
| **name_with_unit**    | Long text        | Medication name with unit (primary key)                                                              |
| **Name**              | Single line text | Medication name                                                                                      |
| **единица измерения** | Single select    | Unit of measurement                                                                                  |
| **in stock**          | Number           | Quantity in stock                                                                                    |
| **Расположение**      | Single select    | Storage location                                                                                     |
| **new_location**      | Single select    | New location system: 1. СИСТЕМНЫЕ И ОБЩИЕ, 2. ЖКТ, ПЕЧЕНЬ, ПОЧКИ, ПАРАЗИТЫ, 3. ИНФЕКЦИИ, Холодильник |
| **ПАКЕТ**             | Single select    | Medication package/category                                                                          |
| **Годен до**          | Single line text | Expiration date text                                                                                 |
| **EXP**               | Date             | Expiration date                                                                                      |
| **Med_location**      | Formula          | Combined location information                                                                        |


---

### 9. intake_release (Intake/Release Events)

Manages scheduled intake and release events for cats.

#### Key Fields


| Field Name        | Type             | Description                                                                    |
| ----------------- | ---------------- | ------------------------------------------------------------------------------ |
| **Name**          | Single line text | Event name (primary key)                                                       |
| **Notes**         | Long text        | Event notes                                                                    |
| **Status**        | Single select    | Event status: Запланировано (Planned), Активно (Active), Завершено (Completed) |
| **Type**          | Single select    | Event type: приёмка (intake), выдача (release)                                 |
| **Date**          | Date             | Event date                                                                     |
| **requests**      | Linked record    | Linked sterilization requests                                                  |
| **SendMessage**   | Button           | Trigger message sending                                                        |
| **MessageStatus** | Single select    | Message status: Не отправлено (Not sent), Отправлено (Sent)                    |


---

### 10. *intake*release (Intake/Release Templates)

Stores message templates for intake/release communications.

#### Key Fields


| Field Name           | Type             | Description                                                                                                  |
| -------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------ |
| **Name**             | Single line text | Template name (primary key)                                                                                  |
| **message_template** | Long text        | Message template content                                                                                     |
| **Status**           | Single select    | Status: Создана (Created), Стерилизация назначена (Sterilization scheduled), Письмо отправлено (Letter sent) |
| **date**             | Date             | Associated date                                                                                              |
| **requestors**       | Linked record    | Linked sterilization requests                                                                                |


---

### 11. cat_travel_prep (International Cat Travel Preparation)

Tracks preparation for international cat travel, including documentation and health requirements.

#### Key Fields


| Field Name                   | Type             | Description                       |
| ---------------------------- | ---------------- | --------------------------------- |
| **catName**                  | Single line text | Cat's name (primary key)          |
| **sterilization_request**    | Linked record    | Link to original request          |
| **chipImplanted**            | Checkbox         | Microchip implanted               |
| **chipNumber**               | Number           | Microchip number                  |
| **chipImplantationDate**     | Date             | Chip implantation date            |
| **chipStickerAdded**         | Checkbox         | Chip sticker added to passport    |
| **titerTestDone**            | Checkbox         | Rabies titer test completed       |
| **titerSubmissionDate**      | Date             | Titer test submission date        |
| **daysSinceTiterReady**      | Formula          | Days since titer test ready       |
| **requiredWaitPeriod**       | Number           | Required waiting period (days)    |
| **waitCompleted**            | Formula          | Waiting period completed          |
| **rabiesVaccineDate**        | Date             | Rabies vaccination date           |
| **rabiesVaccine**            | Checkbox         | Rabies vaccine administered       |
| **complexVaccine**           | Checkbox         | Complex vaccine administered      |
| **parasidesStickerAndStamp** | Checkbox         | Parasite treatment documented     |
| **fleeTreatmentSticker**     | Checkbox         | Flea treatment documented         |
| **medCertificate**           | Checkbox         | Medical certificate obtained      |
| **vetName**                  | Single line text | Veterinarian name                 |
| **photo**                    | Attachment       | Cat photos                        |
| **description**              | Long text        | Additional notes                  |
| **catReadyChecklist**        | Formula          | Comprehensive readiness checklist |


#### Contact Links


| Field Name                  | Type          | Description                   |
| --------------------------- | ------------- | ----------------------------- |
| **fosterContact**           | Linked record | Foster contact                |
| **deliveryToTiterClinic**   | Linked record | Titer clinic delivery contact |
| **deliveryToMinistry**      | Linked record | Ministry delivery contact     |
| **handler**                 | Linked record | Handler contact               |
| **tripCompanionSearch**     | Linked record | Trip companion search contact |
| **tripCompanion**           | Linked record | Confirmed trip companion      |
| **PRContact**               | Linked record | PR/media contact              |
| **recipientNameAndAddress** | Linked record | Recipient contact             |


---

### 12. cat_travel_contacts (Travel Contacts)

Stores contact information for people involved in cat travel.

#### Key Fields


| Field Name          | Type             | Description                                                                       |
| ------------------- | ---------------- | --------------------------------------------------------------------------------- |
| **fullContactInfo** | Formula          | Formatted contact card (primary key)                                              |
| **Name**            | Single line text | Contact name                                                                      |
| **Telegram**        | Single line text | Telegram username                                                                 |
| **Phone**           | Phone number     | Phone number                                                                      |
| **Whatsapp**        | Phone number     | WhatsApp number                                                                   |
| **Address**         | Long text        | Physical address                                                                  |
| **Role**            | Multiple select  | Contact role: Куратор (Curator), Передержка (Foster), Попутчик (Travel companion) |


---

### 13. частота использования лекарств (Medication Usage Frequency)

Tracks medication usage patterns.

#### Key Fields


| Field Name    | Type             | Description                 |
| ------------- | ---------------- | --------------------------- |
| **Name**      | Single line text | Category name (primary key) |
| **в наличии** | Linked record    | Linked medications          |


---

## Table Relationships Diagram

The following describes the key relationships between tables:

```
sterilization_request (Central Hub)
    ├── cat_flat_fostering (1:many) — Fostering records
    │       ├── MedicalCare (1:many) — Medical treatments
    │       │       └── TreatmentDays (1:many) — Daily treatment logs
    │       │               └── shedule (many:1) — Volunteer assignments
    │       └── в наличии / в наличии 2 — Medication lookups
    ├── inventory (many:many) — Equipment loans
    ├── intake_release (many:many) — Intake/release events
    ├── _intake_release (many:many) — Communication templates
    └── cat_travel_prep (1:many) — Travel preparation
            └── cat_travel_contacts (many:many) — Travel contacts

```

---

## Bot Integration Recommendations

### Primary Data Entry Points

**For new sterilization requests**, the bot should create records in the **sterilization_request** table with the following minimum required fields:

1. **requestor_name** — Requestor's name
2. **phone** or **telegram** — At least one contact method
3. **address** — Physical address
4. **district** — City district
5. **sex** — Cat's sex
6. **cat_type** — Domestic or street cat
7. **language** — Communication language preference
8. **created_date** — Set to current date
9. **status** — Set to "Новая заявка" (New request)

### Recommended Bot Workflow

1. **Language Detection**: Determine user's language (ru/en/ka) and set the **language** field accordingly
2. **Contact Collection**: Gather phone, telegram, whatsapp, viber, email, instagram as available
3. **Location Information**: Collect address and district, optionally geo_location link
4. **Cat Details**: Collect sex, cat_type, wild_or_tame, health status, pregnancy status, weight estimate
5. **Service Preferences**: Collect clinic preference, catch_type, needs_foster_care, need_carrier, return_type
6. **Payment Information**: Collect payment_choice based on cat_type
7. **Vaccination Requests**: Collect complex_req and rabies_req checkboxes
8. **Photo Upload**: Collect cat_picture attachment
9. **Additional Notes**: Collect any health_notes, pregnant_notes, or general notes

### Status Workflow

The bot should understand the status progression:

1. **Новая заявка** → Initial submission
2. **Коммуникация с заявителем** → Operator is communicating
3. **Стерилизация назначена** → Date scheduled
4. **На пути в котодом** → Cat in transit
5. **принята в кк** → Cat accepted at facility
6. **Возвращена заявителю** → Cat returned
7. **Стерилизация отменена** → Cancelled
8. **Заявитель перестал отвечать** → No response from requestor

### Multilingual Support

All single-select fields support three languages. The bot should:

- Present options in the user's preferred language
- Store values in the appropriate language variant
- The system uses formula fields to normalize values for reporting

### API Considerations

When integrating via API:

- Use field IDs for reliable field references
- Respect synced table restrictions (в наличии, в наличии 2, shedule are read-only)
- Handle attachment uploads separately for cat_picture field
- Use the **id** (Autonumber) field as the primary reference for requests
- The **record_id** formula field provides the Airtable record ID if needed

---

## Conclusion

The **sterilization_main** database provides a comprehensive system for managing cat sterilization operations. For bot integration, the primary focus should be on the **sterilization_request** table, which serves as the entry point for all new requests. The bot should collect requestor information, cat details, service preferences, and payment information while respecting the multilingual nature of the system. Secondary tables handle fostering, medical care, inventory, and travel preparation, which are typically managed by operators rather than the bot directly.