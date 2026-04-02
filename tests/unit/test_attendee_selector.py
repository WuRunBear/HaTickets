"""Unit tests for AttendeeSelector."""
from unittest.mock import MagicMock
import pytest
from mobile.attendee_selector import AttendeeSelector


class TestEnsureSelected:
    def test_selects_correct_number(self):
        d = MagicMock()
        config = MagicMock()
        config.users = ["user1", "user2"]
        selector = AttendeeSelector(device=d, config=config)
        cb1, cb2, cb3 = MagicMock(), MagicMock(), MagicMock()
        selector._find_checkboxes = MagicMock(return_value=[cb1, cb2, cb3])
        selector._click_checkbox = MagicMock()
        selector.ensure_selected()
        assert selector._click_checkbox.call_count == 2

    def test_no_checkboxes_found(self):
        d = MagicMock()
        config = MagicMock()
        config.users = ["user1"]
        selector = AttendeeSelector(device=d, config=config)
        selector._find_checkboxes = MagicMock(return_value=[])
        selector.ensure_selected()  # should not crash

    def test_single_user(self):
        d = MagicMock()
        config = MagicMock()
        config.users = ["user1"]
        selector = AttendeeSelector(device=d, config=config)
        cb1 = MagicMock()
        selector._find_checkboxes = MagicMock(return_value=[cb1])
        selector._click_checkbox = MagicMock()
        selector.ensure_selected()
        assert selector._click_checkbox.call_count == 1

    def test_empty_users_defaults_to_one(self):
        d = MagicMock()
        config = MagicMock()
        config.users = []
        selector = AttendeeSelector(device=d, config=config)
        cb1 = MagicMock()
        selector._find_checkboxes = MagicMock(return_value=[cb1])
        selector._click_checkbox = MagicMock()
        selector.ensure_selected()
        assert selector._click_checkbox.call_count == 1
