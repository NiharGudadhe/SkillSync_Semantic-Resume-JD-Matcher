import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui_helpers import stretch_call


def test_uses_new_width_argument_when_supported():
    def new_widget(label, width=None, use_container_width=None):
        return ("new", label, width, use_container_width)

    assert stretch_call(new_widget, "Go") == ("new", "Go", "stretch", None)


def test_falls_back_to_old_argument_on_older_versions():
    def old_widget(label, use_container_width=False):  # no `width` parameter
        return ("old", label, use_container_width)

    assert stretch_call(old_widget, "Go") == ("old", "Go", True)


def test_passes_other_arguments_through():
    def old_widget(label, type=None, use_container_width=False):
        return (label, type, use_container_width)

    assert stretch_call(old_widget, "Go", type="primary") == ("Go", "primary", True)


if __name__ == "__main__":
    test_uses_new_width_argument_when_supported()
    test_falls_back_to_old_argument_on_older_versions()
    test_passes_other_arguments_through()
    print("All UI helper tests passed!")