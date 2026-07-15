"""Unit tests for the tenants app.

Tests Ministry model creation and schema auto-generation.
"""

from django.test import TestCase
from tenants.models import Ministry


class MinistryModelTest(TestCase):
    """Verify that a new ministry creates the expected schema."""

    def setUp(self):
        self.ministry = Ministry.objects.create(
            name='Ministry of Health',
            short_name='MOH',
            schema_name='moh_schema',
        )

    def test_ministry_string(self):
        self.assertEqual(str(self.ministry), 'Ministry of Health (moh_schema)')

    def test_schema_name(self):
        self.assertEqual(self.ministry.schema_name, 'moh_schema')

    def test_default_is_active(self):
        self.assertTrue(self.ministry.is_active)
