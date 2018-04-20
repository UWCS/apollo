import os
import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from karma.parser import parse_message, create_transactions, RawKarma, KarmaTransaction
from models import Base


class TestKarmaProcessor(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(create_transactions('', '', []), None)

    def test_simple_positive(self):
        self.assertEqual(create_transactions('Baz', 'Baz', [RawKarma(name='Foobar', op='++', reason=None)]), [
            KarmaTransaction(name='Foobar', self_karma=False, net_karma=1, reasons=[])
        ])

    def test_simple_negative(self):
        self.assertEqual(create_transactions('Baz', 'Baz', [RawKarma(name='Foobar', op='--', reason=None)]), [
            KarmaTransaction(name='Foobar', self_karma=False, net_karma=-1, reasons=[])
        ])

    def test_simple_neutral(self):
        self.assertEqual(create_transactions('Baz', 'Baz', [RawKarma(name='Foobar', op='+-', reason=None)]), [
            KarmaTransaction(name='Foobar', self_karma=False, net_karma=0, reasons=[])
        ])

    def test_self_karma_single(self):
        self.assertEqual(create_transactions('Baz', 'Baz', [RawKarma(name='Baz', op='++', reason=None)]), [
            KarmaTransaction(name='Baz', self_karma=True, net_karma=1, reasons=[])
        ])

    def test_self_karma_multiple(self):
        self.assertEqual(create_transactions('Baz', 'Baz', [
            RawKarma(name='Baz', op='++', reason=None),
            RawKarma(name='Baz', op='++', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=True, net_karma=1, reasons=[])
                         ])

    def test_self_karma_single_with_others(self):
        self.assertEqual(create_transactions('Baz', 'Baz', [
            RawKarma(name='Baz', op='++', reason=None),
            RawKarma(name='Foobar', op='++', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=True, net_karma=1, reasons=[]),
                             KarmaTransaction(name='Foobar', self_karma=False, net_karma=1, reasons=[])
                         ])

    def test_karma_double_positive(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='++', reason=None),
            RawKarma(name='Baz', op='++', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=1, reasons=[])
                         ])

    def test_karma_double_negative(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='--', reason=None),
            RawKarma(name='Baz', op='--', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=-1, reasons=[])
                         ])

    def test_karma_double_neutral(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='+-', reason=None),
            RawKarma(name='Baz', op='-+', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=0, reasons=[])
                         ])

    def test_karma_positive_neutral(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='++', reason=None),
            RawKarma(name='Baz', op='+-', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=1, reasons=[])
                         ])

    def test_karma_negative_neutral(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='--', reason=None),
            RawKarma(name='Baz', op='+-', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=-1, reasons=[])
                         ])

    def test_karma_negative_positive(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='--', reason=None),
            RawKarma(name='Baz', op='++', reason=None)
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=0, reasons=[])
                         ])

    def test_simple_positive_reason(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='++', reason='Foobar is baz')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=1, reasons=['Foobar is baz'])
                         ])

    def test_simple_negative_reason(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='--', reason='Foobar is baz')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=-1, reasons=['Foobar is baz'])
                         ])

    def test_simple_neutral_reason(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='+-', reason='Foobar is baz')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=0,
                                              reasons=['Foobar is baz'])
                         ])

    def test_self_karma_single_reason(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Bar', op='++', reason='Is awesome')
        ]), [
                             KarmaTransaction(name='Bar', self_karma=True, net_karma=1, reasons=['Is awesome'])
                         ])

    def test_self_karma_multiple_reason(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Bar', op='++', reason='Is awesome'),
            RawKarma(name='Bar', op='++', reason='Is awesome')
        ]), [
                             KarmaTransaction(name='Bar', self_karma=True, net_karma=1,
                                              reasons=['Is awesome', 'Is awesome'])
                         ])

    def test_self_karma_single_with_others_and_reasons(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Bar', op='++', reason='Is awesome'),
            RawKarma(name='Foo', op='++', reason='Is awesome too'),
        ]), [
                             KarmaTransaction(name='Bar', self_karma=True, net_karma=1, reasons=['Is awesome']),
                             KarmaTransaction(name='Foo', self_karma=False, net_karma=1, reasons=['Is awesome too'])
                         ])

    def test_karma_double_positive_reasons(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='++', reason='Foobar baz 1'),
            RawKarma(name='Baz', op='++', reason='Foobar baz 2')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=1,
                                              reasons=['Foobar baz 1', 'Foobar baz 2'])
                         ])

    def test_karma_double_negative_reasons(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='--', reason='Foobar baz 1'),
            RawKarma(name='Baz', op='--', reason='Foobar baz 2')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=-1,
                                              reasons=['Foobar baz 1', 'Foobar baz 2'])
                         ])

    def test_karma_double_neutral_reasons(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='-+', reason='Foobar baz 1'),
            RawKarma(name='Baz', op='+-', reason='Foobar baz 2')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=0,
                                              reasons=['Foobar baz 1', 'Foobar baz 2'])
                         ])

    def test_karma_positive_neutral_reasons(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='++', reason='Foobar baz 1'),
            RawKarma(name='Baz', op='+-', reason='Foobar baz 2')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=1,
                                              reasons=['Foobar baz 1', 'Foobar baz 2'])
                         ])

    def test_karma_negative_neutral_reasons(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='--', reason='Foobar baz 1'),
            RawKarma(name='Baz', op='+-', reason='Foobar baz 2')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=-1,
                                              reasons=['Foobar baz 1', 'Foobar baz 2'])
                         ])

    def test_karma_positive_negative_reasons(self):
        self.assertEqual(create_transactions('Bar', 'Bar', [
            RawKarma(name='Baz', op='++', reason='Foobar baz 1'),
            RawKarma(name='Baz', op='--', reason='Foobar baz 2')
        ]), [
                             KarmaTransaction(name='Baz', self_karma=False, net_karma=0,
                                              reasons=['Foobar baz 1', 'Foobar baz 2'])
                         ])


class TestKarmaParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate the testing config for Alembic
        config = Config(os.path.join(os.path.dirname(__file__), '../alembic.tests.ini'))

        # Start up the in-memory database instance
        db_engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(db_engine)
        cls.db_session = Session(bind=db_engine)

        # Make sure it's been updated with migrations
        command.stamp(config, 'head')

    @classmethod
    def tearDownClass(cls):
        cls.db_session = None

    def test_empty(self):
        self.assertEqual(parse_message('', self.db_session), None)

    def test_empty_with_code_block(self):
        self.assertEqual(parse_message('```FoobarBaz```', self.db_session), None)

    def test_simple_positive(self):
        self.assertEqual(parse_message('Foobar++', self.db_session), [RawKarma(name='Foobar', op='++', reason=None)])

    def test_simple_negative(self):
        self.assertEqual(parse_message('Foobar--', self.db_session), [RawKarma(name='Foobar', op='--', reason=None)])

    def test_simple_neutral_pm(self):
        self.assertEqual(parse_message('Foobar+-', self.db_session), [RawKarma(name='Foobar', op='+-', reason=None)])

    def test_simple_neutral_mp(self):
        self.assertEqual(parse_message('Foobar-+', self.db_session), [RawKarma(name='Foobar', op='-+', reason=None)])

    def test_quoted_positive(self):
        self.assertEqual(parse_message('"Foobar"++', self.db_session), [RawKarma(name='Foobar', op='++', reason=None)])

    def test_quoted_negative(self):
        self.assertEqual(parse_message('"Foobar"--', self.db_session), [RawKarma(name='Foobar', op='--', reason=None)])

    def test_quoted_neutral_pm(self):
        self.assertEqual(parse_message('"Foobar"+-', self.db_session), [RawKarma(name='Foobar', op='+-', reason=None)])

    def test_quoted_neutral_mp(self):
        self.assertEqual(parse_message('"Foobar"-+', self.db_session), [RawKarma(name='Foobar', op='-+', reason=None)])

    def test_simple_positive_with_text_after(self):
        self.assertEqual(parse_message('Foobar++ since it\'s pretty cool', self.db_session),
                         [RawKarma(name='Foobar', op='++', reason=None)])

    def test_simple_positive_with_parenthesis_after(self):
        self.assertEqual(parse_message('Foobar++ (hella cool)', self.db_session),
                         [RawKarma(name='Foobar', op='++', reason='hella cool')])

    def test_simple_positive_with_empty_parenthesis_after(self):
        self.assertEqual(parse_message('Foobar++ ()', self.db_session),
                         [RawKarma(name='Foobar', op='++', reason=None)])

    def test_simple_positive_with_compound_reason(self):
        self.assertEqual(parse_message('Foobar++ because it is (hella cool)', self.db_session),
                         [RawKarma(name='Foobar', op='++', reason='it is (hella cool)')])

    def test_simple_positive_with_reason(self):
        self.assertEqual(parse_message('Foobar++ because baz', self.db_session),
                         [RawKarma(name='Foobar', op='++', reason='baz')])

    def test_simple_negative_with_reason(self):
        self.assertEqual(parse_message('Foobar-- because baz', self.db_session),
                         [RawKarma(name='Foobar', op='--', reason='baz')])

    def test_simple_neutral_pm_with_reason(self):
        self.assertEqual(parse_message('Foobar+- because baz', self.db_session),
                         [RawKarma(name='Foobar', op='+-', reason='baz')])

    def test_simple_neutral_mp_with_reason(self):
        self.assertEqual(parse_message('Foobar-+ because baz', self.db_session),
                         [RawKarma(name='Foobar', op='-+', reason='baz')])

    def test_quoted_positive_with_reason(self):
        self.assertEqual(parse_message('"Foobar"++ because baz', self.db_session),
                         [RawKarma(name='Foobar', op='++', reason='baz')])

    def test_quoted_negative_with_reason(self):
        self.assertEqual(parse_message('"Foobar"-- because baz', self.db_session),
                         [RawKarma(name='Foobar', op='--', reason='baz')])

    def test_quoted_neutral_pm_with_reason(self):
        self.assertEqual(parse_message('"Foobar"+- because baz', self.db_session),
                         [RawKarma(name='Foobar', op='+-', reason='baz')])

    def test_quoted_neutral_mp_with_reason(self):
        self.assertEqual(parse_message('"Foobar"-+ because baz', self.db_session),
                         [RawKarma(name='Foobar', op='-+', reason='baz')])

    def test_simple_multiple_karma(self):
        self.assertEqual(parse_message('Foobar++, Baz-- Blat+-', self.db_session), [
            RawKarma(name='Foobar', op='++', reason=None),
            RawKarma(name='Baz', op='--', reason=None),
            RawKarma(name='Blat', op='+-', reason=None)
        ])

    def test_simple_multiple_karma_with_some_reasons_and_quotes(self):
        self.assertEqual(parse_message('Foobar++ because baz blat, "Hello world"--', self.db_session), [
            RawKarma(name='Foobar', op='++', reason='baz blat'),
            RawKarma(name='Hello world', op='--', reason=None)
        ])

    def test_karma_op_no_token(self):
        self.assertEqual(parse_message('++', self.db_session), None)

    def test_simple_invalid(self):
        self.assertEqual(parse_message('Foo+', self.db_session), None)

    def test_simple_not_start_of_sentence(self):
        self.assertEqual(parse_message('Hello, world! Foo++', self.db_session),
                         [RawKarma(name='Foo', op='++', reason=None)])

    def test_simple_invalid_with_reason(self):
        self.assertEqual(parse_message('Foo+ because bar', self.db_session), None)

    def test_code_block_with_internal_reason(self):
        self.assertEqual(parse_message('```Foobar baz because foo```', self.db_session), None)

    def test_code_block_with_karma_op_after(self):
        self.assertEqual(parse_message('```Foobar baz```++', self.db_session), None)

    def test_code_block_external_reason(self):
        self.assertEqual(parse_message('```Foobar baz``` because foo', self.db_session), None)

    def test_code_block_with_karma_op_after_and_external_reason(self):
        self.assertEqual(parse_message('```Foobar baz```++ because foo', self.db_session), None)


if __name__ == '__main__':
    unittest.main()
