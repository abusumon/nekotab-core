"""Regression tests for DebateXML archive parsing.

These cover the bug that made *every* archive import fail: the exporter wrote
`speech/@reply` as "True"/"False" via `str(bool)` while the importer matched
`[@reply='false']` inside an XPath predicate. The predicate matched nothing, so
`substantive_speakers` was inferred as 0, `Tournament.positions` came back
empty, the loop that assigns speaker scores never ran, and every scoresheet
ended up a 0-0 tie that `HighPointWinsRequiredScoresheet` rejects — surfacing
five call frames away as "Tried to save an invalid result".

Nothing here needs a database, so it runs with plain `SimpleTestCase`.
"""

from xml.etree.ElementTree import fromstring

from django.test import SimpleTestCase

from importer.archive import Importer, xml_bool


class XMLBoolTests(SimpleTestCase):

    def test_accepts_both_cases(self):
        for value in ('true', 'True', 'TRUE', ' true '):
            self.assertTrue(xml_bool(value), f'{value!r} should parse as True')
        for value in ('false', 'False', 'FALSE', ' false '):
            self.assertFalse(xml_bool(value), f'{value!r} should parse as False')

    def test_missing_attribute_is_false(self):
        # ElementTree returns None for an absent attribute; that must not raise
        # and must not read as true.
        self.assertFalse(xml_bool(None))
        self.assertFalse(xml_bool(''))

    def test_unrecognised_value_is_false(self):
        self.assertFalse(xml_bool('yes'))
        self.assertFalse(xml_bool('1'))


class ConsensusDetectionTests(SimpleTestCase):
    """`_is_consensus_ballot` reads only the XML, so it needs no database."""

    def _archive(self, elimination, ballots_per_side):
        sides = ''.join(
            '<side team="T1">{}</side>'.format(
                ''.join('<ballot rank="1">250.0</ballot>' for _ in range(ballots_per_side)))
            for _ in range(2))
        return fromstring(
            '<tournament name="T">'
            f'<round elimination="{elimination}"><debate id="D1">{sides}</debate></round>'
            '</tournament>')

    def test_one_ballot_per_side_is_consensus(self):
        importer = Importer(self._archive('false', 1))
        self.assertTrue(importer._is_consensus_ballot(False))

    def test_several_ballots_per_side_is_per_adjudicator(self):
        importer = Importer(self._archive('false', 3))
        self.assertFalse(importer._is_consensus_ballot(False))

    def test_capitalised_elimination_still_matches(self):
        """The regression: a capitalised attribute used to match no rounds at
        all, so the counts were 0 == 0 and every tournament looked like it used
        consensus ballots regardless of what it actually used."""
        importer = Importer(self._archive('False', 3))
        self.assertFalse(importer._is_consensus_ballot(False))

        importer = Importer(self._archive('True', 1))
        self.assertTrue(importer._is_consensus_ballot(True))


class SubstantiveSpeakerCountTests(SimpleTestCase):
    """The count that was silently returning 0 for every archive ever written."""

    def _speeches(self, reply_values):
        speeches = ''.join(f'<speech reply="{v}"><ballot>75.0</ballot></speech>'
                           for v in reply_values)
        return fromstring(
            '<tournament name="T"><round elimination="false"><debate id="D1">'
            f'<side team="T1">{speeches}</side>'
            '</debate></round></tournament>')

    def _count(self, root):
        # Mirrors the inference in Importer.set_preferences.
        return sum(1 for speech in root.findall("round[1]/debate[1]/side[1]/speech")
                   if not xml_bool(speech.get('reply')))

    def test_counts_lowercase(self):
        self.assertEqual(self._count(self._speeches(['false', 'false', 'false', 'true'])), 3)

    def test_counts_capitalised(self):
        """What Tabbycat's own exporter actually emitted. This returned 0 before
        the fix, which is what wiped out every speaker score on import."""
        self.assertEqual(self._count(self._speeches(['False', 'False', 'False', 'True'])), 3)

    def test_no_reply_speech(self):
        self.assertEqual(self._count(self._speeches(['False', 'False'])), 2)


class ImporterRequiresOrganizationTests(SimpleTestCase):
    """Tournament.organization is NOT NULL, so an importer without one used to
    fail with an IntegrityError from deep inside save(). It should say so
    up front instead."""

    def test_missing_organization_raises_clear_error(self):
        importer = Importer(fromstring('<tournament name="T"/>'))
        with self.assertRaisesMessage(ValueError, 'requires an organization'):
            importer.import_tournament()
