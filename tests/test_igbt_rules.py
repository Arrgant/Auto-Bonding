"""IGBT rule suite."""

import pytest

from core import (
    DRCChecker,
    DRCMode,
    BondingDiagramConverter,
    IGBTPadType,
    IGBTRules,
    IGBT_RULES_AUTOMOTIVE,
    IGBT_RULES_DEFAULT,
    IGBT_RULES_HIGH_VOLTAGE,
    WireType,
)


class TestIGBTRules:
    """Basic IGBT rule tests."""

    def test_default_rules(self):
        rules = IGBTRules()

        assert rules.min_spacing_low_voltage == 0.5
        assert rules.min_spacing_medium_voltage == 1.0
        assert rules.min_spacing_high_voltage == 2.0
        assert rules.min_spacing_ultra_high_voltage == 3.0

    def test_default_preset_is_usable(self):
        assert IGBT_RULES_DEFAULT.min_spacing_medium_voltage == 1.0

    def test_voltage_spacing(self):
        rules = IGBTRules()

        assert rules.get_min_spacing_for_voltage(50) == 0.5
        assert rules.get_min_spacing_for_voltage(100) == 0.5
        assert rules.get_min_spacing_for_voltage(300) == 1.0
        assert rules.get_min_spacing_for_voltage(600) == 1.0
        assert rules.get_min_spacing_for_voltage(800) == 2.0
        assert rules.get_min_spacing_for_voltage(1200) == 2.0
        assert rules.get_min_spacing_for_voltage(1500) == 3.0
        assert rules.get_min_spacing_for_voltage(3300) == 3.0

    def test_current_capacity_al_wire(self):
        rules = IGBTRules()

        current_100 = rules.get_current_capacity(0.1, WireType.AL_WIRE)
        current_300 = rules.get_current_capacity(0.3, WireType.AL_WIRE)
        current_500 = rules.get_current_capacity(0.5, WireType.AL_WIRE)

        assert current_100 > 0
        assert current_300 > current_100
        assert current_500 > current_300

    def test_current_capacity_ribbon(self):
        rules = IGBTRules()
        current = rules.get_current_capacity(0.1, WireType.AL_RIBBON)
        assert current > 0

    def test_loop_height_coefficient(self):
        rules = IGBTRules()

        assert rules.loop_height_coefficient_al_wire > 1.5
        assert rules.loop_height_coefficient_al_ribbon > 1.0

    def test_pad_size_validation(self):
        rules = IGBTRules()

        violations = rules.validate_pad_type(IGBTPadType.EMITTER, 0.2)
        assert len(violations) > 0

        violations = rules.validate_pad_type(IGBTPadType.EMITTER, 0.4)
        assert len(violations) == 0

        violations = rules.validate_pad_type(IGBTPadType.COLLECTOR, 0.3)
        assert len(violations) > 0

        violations = rules.validate_pad_type(IGBTPadType.GATE, 0.15)
        assert len(violations) > 0


class TestIGBTDRC:
    """IGBT DRC mode tests."""

    def test_drc_mode_standard(self):
        checker = DRCChecker(mode=DRCMode.STANDARD)
        assert not checker.is_igbt

    def test_drc_mode_igbt(self):
        checker = DRCChecker(mode=DRCMode.IGBT)
        assert checker.is_igbt
        assert checker.rules.get("min_pad_size_emitter") == 0.3
        assert checker.rules.get("min_pad_size_collector") == 0.5

    def test_drc_mode_automotive(self):
        checker = DRCChecker(mode=DRCMode.AUTOMOTIVE)
        assert checker.is_igbt

    def test_igbt_rules_loaded(self):
        checker = DRCChecker(mode=DRCMode.IGBT)

        assert "min_spacing_low_voltage" in checker.rules
        assert "min_spacing_high_voltage" in checker.rules
        assert "max_loop_height_wire" in checker.rules
        assert "current_density_al_wire" in checker.rules


class TestIGBTPresets:
    """IGBT preset tests."""

    def test_high_voltage_preset(self):
        rules = IGBT_RULES_HIGH_VOLTAGE

        assert rules.min_spacing_high_voltage == 2.5
        assert rules.min_spacing_ultra_high_voltage == 4.0
        assert rules.max_loop_height_wire == 4.0

    def test_automotive_preset(self):
        rules = IGBT_RULES_AUTOMOTIVE

        assert rules.min_spacing_medium_voltage == 1.2
        assert rules.min_spacing_high_voltage == 2.2
        assert rules.fatigue_factor_al == 1.2
        assert rules.max_temperature_rise == 40.0


class TestIGBTConverter:
    """IGBT converter integration tests."""

    def test_igbt_converter_init(self):
        converter = BondingDiagramConverter(
            {
                "mode": "igbt",
                "default_wire_diameter": 0.3,
                "default_material": "aluminum",
            }
        )

        assert converter.is_igbt
        assert converter.mode == "igbt"
        assert converter.default_wire_diameter == 0.3
        assert converter.default_material == "aluminum"
        assert converter.wire_type == "al_wire"

    def test_igbt_loop_height_calculation(self):
        converter_igbt = BondingDiagramConverter({"mode": "igbt"})
        converter_std = BondingDiagramConverter({"mode": "standard"})

        span = 5.0
        diameter = 0.3

        h_igbt = converter_igbt.calculate_loop_height(span, diameter, "aluminum")
        h_std = converter_std.calculate_loop_height(span, diameter, "aluminum")

        assert h_igbt > h_std

    def test_automotive_thermal_compensation(self):
        converter_auto = BondingDiagramConverter({"mode": "automotive"})
        converter_igbt = BondingDiagramConverter({"mode": "igbt"})

        span = 5.0
        diameter = 0.3

        h_auto = converter_auto.calculate_loop_height(span, diameter, "aluminum")
        h_igbt = converter_igbt.calculate_loop_height(span, diameter, "aluminum")

        assert h_auto > h_igbt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
