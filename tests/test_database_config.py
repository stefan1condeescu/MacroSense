import os
import unittest
from unittest.mock import Mock, patch

import database


class DatabaseConfigurationTests(unittest.TestCase):
    def test_environment_setting_overrides_default(self):
        with patch.dict(os.environ, {"DB_NAME": "custom_db"}, clear=False):
            self.assertEqual(database._get_setting("DB_NAME", "macrosense_db"), "custom_db")

    def test_connection_requires_an_explicit_password(self):
        with (
            patch.object(database, "_get_setting", return_value=None),
            patch.object(database.psycopg2, "connect") as connect_mock,
            patch.object(database.st, "error") as error_mock,
        ):
            self.assertIsNone(database.get_connection())

        connect_mock.assert_not_called()
        error_mock.assert_called_once()

    def test_connection_uses_environment_configuration(self):
        configured_environment = {
            "DB_HOST": "db.example.test",
            "DB_PORT": "6543",
            "DB_NAME": "macrosense_test",
            "DB_USER": "macrosense_user",
            "DB_PASSWORD": "test-only-password",
        }
        expected_connection = Mock()

        with (
            patch.dict(os.environ, configured_environment, clear=True),
            patch.object(database.psycopg2, "connect", return_value=expected_connection) as connect_mock,
        ):
            self.assertIs(database.get_connection(), expected_connection)

        connect_mock.assert_called_once_with(
            dbname="macrosense_test",
            user="macrosense_user",
            password="test-only-password",
            host="db.example.test",
            port="6543",
        )


if __name__ == "__main__":
    unittest.main()
