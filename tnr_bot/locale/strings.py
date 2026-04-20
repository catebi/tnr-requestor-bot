"""UI strings for en / ru / ka. Keys are stable English identifiers."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "error.need_public_username_start": (
            "Set a public Telegram username in Settings so we can match your sterilization "
            "form. Then send /start or /myrequests again."
        ),
        "error.need_public_username_contact": (
            "Set a public Telegram username in Settings so we can match your sterilization "
            "form. Then send /contact again."
        ),
        "error.need_public_username_language": (
            "Set a public Telegram username in Settings so we can match your sterilization "
            "form. Then send /language again."
        ),
        "error.airtable_unavailable": (
            "Could not reach the database. Check server configuration and try again later."
        ),
        "error.generic": "Something went wrong. Try again later.",
        "error.operators_unavailable": "Could not load the operators directory. Try again later.",
        "no_requests": (
            "No sterilization requests found for @{username}. "
            "Check that the form’s telegram field matches this handle (with or without @)."
        ),
        "contact.no_operator_yet": (
            "No operator is assigned to your requests yet. "
            "For questions, please write to {fallback}."
        ),
        "contact.header": "Here are your requests and operator contacts on Telegram:\n\n",
        "contact.operator_placeholder": "Operator",
        "contact.part_no_telegram": "{name} (no Telegram in directory)",
        "contact.operator_not_assigned": "• id {rid} · {status} · operator: not assigned yet",
        "contact.line_linked": "• id {rid} · {status} · {parts}",
        "contact.line_label_tg": "• id {rid} · {status} · {label} · {tg}",
        "contact.no_handle_directory": (
            "• id {rid} · {status} · {label} · (no Telegram handle in the operators directory)"
        ),
        "summary.label_id": "id",
        "summary.label_created_date": "created_date",
        "summary.label_status": "status",
        "summary.label_operator": "operator",
        "summary.operator_linked_fallback": "operator (linked)",
        "notify.prefix_new_request": "New sterilization request:\n\n",
        "notify.prefix_operator_assigned": "An operator was assigned to your sterilization request:\n\n",
        "notify.prefix_status_changed": "Your sterilization request status was updated:\n\n",
        "language.choose_prompt": "Choose the language for bot messages:",
        "language.saved": "Saved. Bot language: {native}.",
        "language.no_records": (
            "No sterilization requests were found for your account. "
            "Language is stored on your request rows after you submit the form."
        ),
        "language.patch_failed": "Could not save language. Check the `language` field in Airtable and try again.",
    },
    "ru": {
        "error.need_public_username_start": (
            "Укажите публичный username в Telegram, чтобы мы могли сопоставить вашу заявку "
            "на стерилизацию. Затем снова отправьте /start или /myrequests."
        ),
        "error.need_public_username_contact": (
            "Укажите публичный username в Telegram, чтобы мы могли сопоставить вашу заявку "
            "на стерилизацию. Затем снова отправьте /contact."
        ),
        "error.need_public_username_language": (
            "Укажите публичный username в Telegram, чтобы мы могли сопоставить вашу заявку "
            "на стерилизацию. Затем снова отправьте /language."
        ),
        "error.airtable_unavailable": (
            "Не удалось подключиться к базе. Проверьте настройки сервера и попробуйте позже."
        ),
        "error.generic": "Что-то пошло не так. Попробуйте позже.",
        "error.operators_unavailable": "Не удалось загрузить справочник операторов. Попробуйте позже.",
        "no_requests": (
            "Заявок на стерилизацию для @{username} не найдено. "
            "Проверьте, что поле telegram в форме совпадает с этим username (с @ или без)."
        ),
        "contact.no_operator_yet": (
            "Пока ни к одной из ваших заявок не назначен оператор. "
            "По вопросам напишите: {fallback}."
        ),
        "contact.header": "Ваши заявки и контакты операторов в Telegram:\n\n",
        "contact.operator_placeholder": "Оператор",
        "contact.part_no_telegram": "{name} (нет Telegram в справочнике)",
        "contact.operator_not_assigned": "• id {rid} · {status} · оператор: пока не назначен",
        "contact.line_linked": "• id {rid} · {status} · {parts}",
        "contact.line_label_tg": "• id {rid} · {status} · {label} · {tg}",
        "contact.no_handle_directory": (
            "• id {rid} · {status} · {label} · (нет Telegram в справочнике операторов)"
        ),
        "summary.label_id": "id",
        "summary.label_created_date": "дата_создания",
        "summary.label_status": "статус",
        "summary.label_operator": "оператор",
        "summary.operator_linked_fallback": "оператор (связано)",
        "notify.prefix_new_request": "Новая заявка на стерилизацию:\n\n",
        "notify.prefix_operator_assigned": "К вашей заявке назначен оператор:\n\n",
        "notify.prefix_status_changed": "Статус вашей заявки на стерилизацию обновлён:\n\n",
        "language.choose_prompt": "Выберите язык сообщений бота:",
        "language.saved": "Сохранено. Язык бота: {native}.",
        "language.no_records": (
            "Заявок по вашему аккаунту не найдено. Язык сохраняется в строках заявки после отправки формы."
        ),
        "language.patch_failed": "Не удалось сохранить язык. Проверьте поле `language` в Airtable и попробуйте снова.",
    },
    "ka": {
        "error.need_public_username_start": (
            "დააყენეთ საჯარო Telegram username პარამეტრებში, რათა შევაჯეროთ თქვენი სტერილიზაციის "
            "მოთხოვნა. შემდეგ კვლავ გაგზავნით /start ან /myrequests."
        ),
        "error.need_public_username_contact": (
            "დააყენეთ საჯარო Telegram username პარამეტრებში, რათა შევაჯეროთ თქვენი სტერილიზაციის "
            "მოთხოვნა. შემდეგ კვლავ გაგზავნით /contact."
        ),
        "error.need_public_username_language": (
            "დააყენეთ საჯარო Telegram username პარამეტრებში, რათა შევაჯეროთ თქვენი სტერილიზაციის "
            "მოთხოვნა. შემდეგ კვლავ გაგზავნით /language."
        ),
        "error.airtable_unavailable": (
            "ბაზამდე მიუწვდომელია. შეამოწმეთ სერვერის კონფიგურაცია და სცადეთ მოგვიანებით."
        ),
        "error.generic": "რაღაც შეცდა. სცადეთ მოგვიანებით.",
        "error.operators_unavailable": "ოპერატორების ცნობარი ვერ ჩაიტვირთა. სცადეთ მოგვიანებით.",
        "no_requests": (
            "სტერილიზაციის მოთხოვნა @{username}-ისთვის ვერ მოიძებნა. "
            "დარწმუნდით, რომ ფორმაში telegram ველი ემთხვევა ამ username-ს (@-ით ან მის გარეშე)."
        ),
        "contact.no_operator_yet": (
            "ჯერ არც ერთ მოთხოვნას არ ჰყავს ოპერატორი. "
            "კითხვებისთვის მოგვწერეთ: {fallback}."
        ),
        "contact.header": "თქვენი მოთხოვნები და ოპერატორების კონტაქტები Telegram-ში:\n\n",
        "contact.operator_placeholder": "ოპერატორი",
        "contact.part_no_telegram": "{name} (Telegram ცნობარში არაა)",
        "contact.operator_not_assigned": "• id {rid} · {status} · ოპერატორი: ჯერ არ არის დანიშნული",
        "contact.line_linked": "• id {rid} · {status} · {parts}",
        "contact.line_label_tg": "• id {rid} · {status} · {label} · {tg}",
        "contact.no_handle_directory": (
            "• id {rid} · {status} · {label} · (Telegram ცნობარში არ არის)"
        ),
        "summary.label_id": "id",
        "summary.label_created_date": "შექმნის_თარიღი",
        "summary.label_status": "სტატუსი",
        "summary.label_operator": "ოპერატორი",
        "summary.operator_linked_fallback": "ოპერატორი (დაკავშირებული)",
        "notify.prefix_new_request": "ახალი მოთხოვნა სტერილიზაციაზე:\n\n",
        "notify.prefix_operator_assigned": "თქვენს მოთხოვნას ოპერატორი მიენიჭა:\n\n",
        "notify.prefix_status_changed": "თქვენი მოთხოვნის სტატუსი განახლდა:\n\n",
        "language.choose_prompt": "აირჩიეთ ბოტის შეტყობინებების ენა:",
        "language.saved": "შენახულია. ბოტის ენა: {native}.",
        "language.no_records": (
            "თქვენი ანგარიშით მოთხოვნა ვერ მოიძებნა. ენა ინახება მოთხოვნის სტრიქონზე ფორმის გაგზავნის შემდეგ."
        ),
        "language.patch_failed": "ენის შენახვა ვერ მოხერხდა. შეამოწმეთ Airtable-ში ველი `language` და სცადეთ თავიდან.",
    },
}
