from decimal import Decimal

import pytest

from services import assessment_config
from services.validation import ValidationError
from tests.factories import make_student, make_subject, record_mark


def values_from(config, **overrides):
    """A complete {assessment_id: (max, weight)} mapping equal to the current config."""
    values = {a['assessment_id']: (a['max'], a['weight']) for a in config}
    for code, pair in overrides.items():
        target = next(a for a in config if a['code'] == code)
        values[target['assessment_id']] = pair
    return values


def test_load_config_returns_the_stock_components_in_order(ctx):
    config = assessment_config.load_config()
    assert [(a['code'], a['max'], a['weight']) for a in config] == [
        ('CAT1', 50, 15), ('CAT2', 50, 15), ('CAT3', 50, 15),
        ('ASSIGN', 50, 10), ('PROJECT', 100, 20), ('ENDSEM', 100, 25)]
    assert config[0]['name'] == 'Continuous Assessment Test 1'


def test_weights_can_be_rebalanced_as_long_as_they_total_100(ctx):
    config = assessment_config.load_config()
    changes = assessment_config.update_config(values_from(
        config, CAT1=(Decimal(50), Decimal(10)), ENDSEM=(Decimal(100), Decimal(30))))
    reloaded = {a['code']: a['weight'] for a in assessment_config.load_config()}
    assert reloaded['CAT1'] == 10 and reloaded['ENDSEM'] == 30
    assert any('CAT1' in change for change in changes)


def test_weights_that_do_not_total_100_are_rejected_and_nothing_changes(ctx):
    config = assessment_config.load_config()
    with pytest.raises(ValidationError, match='add up to 100'):
        assessment_config.update_config(values_from(
            config, CAT1=(Decimal(60), Decimal(20)), ENDSEM=(Decimal(80), Decimal(25))))
    assert [(a['max'], a['weight']) for a in assessment_config.load_config()] == [
        (50, 15), (50, 15), (50, 15), (50, 10), (100, 20), (100, 25)]


@pytest.mark.parametrize('maximum, weight, message', [
    (Decimal(0), Decimal(15), 'Maximum'),
    (Decimal(50), Decimal(0), 'Weight'),
    (Decimal(50), Decimal(101), 'Weight'),
])
def test_each_value_is_range_checked(ctx, maximum, weight, message):
    config = assessment_config.load_config()
    with pytest.raises(ValidationError, match=message):
        assessment_config.update_config(values_from(config, CAT1=(maximum, weight)))


def test_a_maximum_cannot_drop_below_marks_already_recorded(ctx):
    student, subject = make_student(), make_subject()
    record_mark(student, subject, 'CAT1', 48)
    config = assessment_config.load_config()
    with pytest.raises(ValidationError, match='CAT1.*48'):
        assessment_config.update_config(values_from(config, CAT1=(Decimal(40), Decimal(15))))
    assert assessment_config.load_config()[0]['max'] == 50


def test_every_component_must_be_supplied(ctx):
    config = assessment_config.load_config()
    partial = values_from(config)
    partial.pop(config[0]['assessment_id'])
    with pytest.raises(ValidationError, match='every'):
        assessment_config.update_config(partial)


def test_to_calculation_config_matches_what_the_calculator_expects(ctx):
    calc = assessment_config.for_calculation(assessment_config.load_config())
    assert calc[0] == {'code': 'CAT1', 'max': Decimal(50), 'weight': Decimal(15)}
