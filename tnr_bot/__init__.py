"""
TNR requestor Telegram bot — package layout:

- ``config`` — environment and credentials
- ``integrations.airtable`` — Airtable API client and query formulas
- ``handlers`` — Telegram command/callback handlers (add new commands here)
- ``utils.formatting`` — user-visible text formatting from records
- ``runtime.transport`` — polling vs webhook startup
- ``app`` — wiring, ``main()`` entry point
"""

__version__ = "0.1.0"
