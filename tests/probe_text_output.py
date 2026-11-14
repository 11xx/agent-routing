"""On-demand faulty variants for the four human output contracts."""

import copy
import io
import unittest
from unittest.mock import patch

from test_text_output import TextOutputTest
import text_output


def missing_section():
    real = text_output.section
    def omitted(lines, heading, entries):
        if heading != "Weaknesses":
            real(lines, heading, entries)
    return patch.object(text_output, "section", side_effect=omitted)


def lost_recurrence():
    real = text_output.note_lines
    def forgotten(row, *args, **opts):
        return real(dict(row, occurrences=1, last_seen=row["date"]), *args, **opts)
    return patch.object(text_output, "note_lines", side_effect=forgotten)


def unchanged_field():
    real = text_output.edit
    def noisy(result, width):
        result = copy.deepcopy(result)
        result["changes"][0]["before"]["provider"] = "invented-previous-provider"
        return real(result, width)
    return patch.object(text_output, "edit", side_effect=noisy)


def subject_only():
    return patch.object(text_output, "history", side_effect=lambda root, edits:
                        [f"{row['commit'][:12]} {row['subject']}" for row in edits])


def no_wrapping():
    real = text_output.wrapped
    return patch.object(text_output, "wrapped", side_effect=lambda text, width, *args, **opts: real(text, 10000, *args, **opts))


PROBES = (
    ("test_card_structure_and_wrapping", missing_section, "missing card section", "Weaknesses section omitted"),
    ("test_notes_coordinates_liveness_and_dates", lost_recurrence, "×2", "recurrence and date range lost"),
    ("test_edit_changed_fields_addition_and_removal", unchanged_field, "unchanged fields were printed", "unchanged provider rendered"),
    ("test_log_one_line_date_verb_row_and_reason", subject_only, "Regex didn't match", "date and verb omitted"),
    ("test_card_structure_and_wrapping", no_wrapping, "output exceeds the requested width", "terminal width ignored"),
)


def run(name):
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.TestSuite([TextOutputTest(name)]))
    return result, output.getvalue()


def main():
    for name, variant, expected, fault in PROBES:
        with variant():
            failed, output = run(name)
        if failed.wasSuccessful() or expected not in output:
            raise AssertionError(f"{fault} did not fail as predicted:\n{output}")
        passed, output = run(name)
        if not passed.wasSuccessful():
            raise AssertionError(output)
        print(f"{name}: faulty FAIL ({fault}); restored PASS", flush=True)


if __name__ == "__main__":
    main()
