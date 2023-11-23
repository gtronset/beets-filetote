"""Test for functions in `filetote_dataclasses`, esp. TypeError validations."""

# pylint: disable=protected-access
import os
import sys
import unittest
from typing import Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from beetsplug import (  # noqa: E402 # pylint: disable=wrong-import-position
    filetote_dataclasses,
)


class TestTypeErrorFunctions(unittest.TestCase):
    """Test for functions in `filetote_dataclasses`, esp. TypeError validations."""

    def test__validate_types_instance(self) -> None:
        """Ensure the instance function correctly checks for the types."""
        # Ensure basic type check
        self._test_instance_validation(["test"], {}, dict, str)

        # Ensure Class type checks
        pairing_dataclass = filetote_dataclasses.FiletotePairingData()

        self._test_instance_validation(
            ["test"],
            pairing_dataclass,
            filetote_dataclasses.FiletotePairingData,
            filetote_dataclasses.FiletoteConfig,
        )

    def _test_instance_validation(
        self,
        field_name: List[str],
        field_value: Any,
        field_type: Any,
        expected_type: Any,
    ) -> None:
        """Helper Function to test that the instance function correctly checks for the
        types."""
        try:
            filetote_dataclasses._validate_types_instance(
                field_name, field_value, field_type
            )
        except TypeError as e:
            self.fail(f"Exception {type(e)} was raised unexpectedly: {e}")

        with self.assertRaises(TypeError) as assert_test_message:
            filetote_dataclasses._validate_types_instance(
                field_name, field_value, expected_type
            )

        assertion_msg: str = (
            "Value for Filetote config key"
            f' "{filetote_dataclasses._format_config_hierarchy(field_name)}" should be'
            f" of type {expected_type}, got `{type(field_value)}`"
        )

        self.assertEqual(
            str(assert_test_message.exception),
            assertion_msg,
        )

    def test__validate_types_dict(self) -> None:
        """Ensure the dict function correctly checks for the types."""
        # Test the positive outcome of dict comparison
        try:
            filetote_dataclasses._validate_types_dict(["test"], {"key": "value"}, str)
        except TypeError as e:
            self.fail(f"Exception {type(e)} was raised unexpectedly: {e}")

        # Fail if the key isn't a string
        with self.assertRaises(TypeError) as non_string_key_test:
            filetote_dataclasses._validate_types_dict(["test"], {123: "value"}, str)

        self.assertEqual(
            str(non_string_key_test.exception),
            'Key "123" for Filetote config key "[test]" should be of type string'
            " (`str`), got `<class 'int'>`",
        )

        # Fail the value doesn't match the type
        with self.assertRaises(TypeError) as wrong_value_type_test:
            filetote_dataclasses._validate_types_dict(["test"], {"key": []}, str)

        self.assertEqual(
            str(wrong_value_type_test.exception),
            'Key "key"\'s Value for Filetote config key "[test]" should be of type'
            " string (`str`), got `<class 'list'>`",
        )

        # Fail the the inner list value isn't a string
        with self.assertRaises(TypeError) as wrong_value_type_test:
            filetote_dataclasses._validate_types_dict(
                ["test"], {"key": [123]}, list, list_subtype=str
            )

        self.assertEqual(
            str(wrong_value_type_test.exception),
            'Value for Filetote config key "[test]" should be of type (inner element'
            " of the list) <class 'str'>, got `<class 'int'>`",
        )

    def test__validate_types_str_eq(self) -> None:
        """Ensure the str_eq correctly checks for the types."""

        # Test the positive outcome of a `List[str]`
        try:
            filetote_dataclasses._validate_types_str_eq(["test"], ["string"], '""')
        except TypeError as e:
            self.fail(f"Exception {type(e)} was raised unexpectedly: {e}")

        # Fail if the value isn't a List
        with self.assertRaises(TypeError) as non_list_test:
            filetote_dataclasses._validate_types_str_eq(["test"], dict, '""')

        self.assertEqual(
            str(non_list_test.exception),
            'Value for Filetote config key "[test]" should be of type literal `""`, an'
            " empty list, or sequence/list of strings (type `List[str]`), got `<class"
            " 'type'>`",
        )

        # Fail the the inner list value isn't a string
        with self.assertRaises(TypeError) as non_string_item_test:
            filetote_dataclasses._validate_types_str_eq(["test"], [123], '""')

        self.assertEqual(
            str(non_string_item_test.exception),
            'Value for Filetote config key "[test]" should be of type sequence/list'
            " of strings (type `List[str]`), got `<class 'int'>`",
        )

    def test__raise_type_validation_error(self) -> None:
        """
        Tests that the formatting for the TypeErrors matches depending on whether
        just a value is specified or also dict keys.
        """
        with self.assertRaises(TypeError) as value_test:
            filetote_dataclasses._raise_type_validation_error(
                ["test"], dict, value="value"
            )

        self.assertEqual(
            str(value_test.exception),
            'Value for Filetote config key "[test]" should be of type <class'
            " 'dict'>, got `<class 'str'>`",
        )

        with self.assertRaises(TypeError) as key_test:
            filetote_dataclasses._raise_type_validation_error(
                ["test"], "<class 'str'>", "dict-value", 12345
            )

        self.assertEqual(
            str(key_test.exception),
            'Key "12345" for Filetote config key "[test]" should be of type <class'
            " 'str'>, got `<class 'int'>`",
        )

        with self.assertRaises(TypeError) as keys_value_test:
            filetote_dataclasses._raise_type_validation_error(
                ["test"], "<class 'str'>", [], 12345, True
            )

        self.assertEqual(
            str(keys_value_test.exception),
            'Key "12345"\'s Value for Filetote config key "[test]" should be of type'
            " <class 'str'>, got `<class 'list'>`",
        )

    def test__format_config_hierarchy(self) -> None:
        """Tests that the output matches the format `[level1][level2[level3]`, etc."""
        single = filetote_dataclasses._format_config_hierarchy(["config"])
        self.assertEqual(single, "[config]")

        multiple = filetote_dataclasses._format_config_hierarchy([
            "top", "middle", "end"
        ])
        self.assertEqual(multiple, "[top][middle][end]")
