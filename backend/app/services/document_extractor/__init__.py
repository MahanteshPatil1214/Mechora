"""MECHORA document-text extraction service (PDF / DOCX / TXT).

Pure extraction only: takes raw bytes plus a filename, returns normalized plain
text. No pipeline logic, no persistence, no inference — callers decide what to
do with the text. Limits (size / character budget) are enforced by the API
routes, not here, so the service stays a dumb, testable string producer.
"""