import unittest
from unittest.mock import patch

from blackbox import dashboard


class DashboardTests(unittest.TestCase):
    @patch("blackbox.dashboard.st.markdown")
    @patch("blackbox.dashboard.st.warning")
    def test_load_css_reads_the_project_style_sheet(self, warning_mock, markdown_mock):
        dashboard.load_css()

        markdown_mock.assert_called_once()
        warning_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
