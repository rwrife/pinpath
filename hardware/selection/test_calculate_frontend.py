import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("calculate_frontend.py")
SPEC = importlib.util.spec_from_file_location("calculate_frontend", MODULE_PATH)
assert SPEC and SPEC.loader
calculator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(calculator)


class FrontEndCalculationTests(unittest.TestCase):
    def test_connected_group_response_is_detectable_at_max_group_size(self):
        analysis = calculator.build_analysis()
        derived = analysis["derived"]
        self.assertGreater(derived["worst_32_node_high_delta_v"], 0.65)
        self.assertLess(derived["worst_32_node_low_delta_v"], -0.40)
        threshold = analysis["provisional_thresholds"]["continuity_min_abs_delta_from_bias_v"]
        self.assertGreater(abs(derived["worst_32_node_high_delta_v"]), threshold * 2)

    def test_open_leakage_budget_is_below_precheck_guard_band(self):
        analysis = calculator.build_analysis()
        error = analysis["derived"]["open_node_leakage_error_budget_v"]
        guard = analysis["provisional_thresholds"]["precheck_low_phase_max_v"]
        self.assertLess(error, guard / 10)

    def test_fault_currents_are_below_selected_part_continuous_ratings(self):
        derived = calculator.build_analysis()["derived"]
        # BAS70-04 is 70 mA continuous; TMUX1108 is 60 mA at 125 C.
        selected_lowest_rating_a = 0.060
        self.assertLess(abs(derived["positive_external_fault"]["clamp_current_a"]), selected_lowest_rating_a)
        self.assertLess(abs(derived["negative_external_fault"]["clamp_current_a"]), selected_lowest_rating_a)
        self.assertLess(derived["driven_endpoint_short_to_ground_current_a"], selected_lowest_rating_a)
        self.assertLess(derived["two_drive_contention_current_a"], selected_lowest_rating_a)

    def test_resistor_power_is_below_standard_mode_rating(self):
        derived = calculator.build_analysis()["derived"]
        rating_w = 0.125
        self.assertLess(derived["positive_external_fault"]["series_resistor_power_w"], rating_w / 10)
        self.assertLess(derived["negative_external_fault"]["series_resistor_power_w"], rating_w / 10)

    def test_conversion_budget_leaves_protocol_overhead(self):
        derived = calculator.build_analysis()["derived"]
        self.assertLess(derived["max_repetition_conversion_budget_s"], 20.0)
        self.assertLess(derived["default_8_repetition_conversion_budget_s"], 3.0)

    def test_fixed_external_sources_fail_two_phase_precheck(self):
        cases = calculator.build_analysis()["derived"]["fixed_external_source_precheck_cases"]
        self.assertTrue(cases)
        self.assertTrue(all(case["overall_pass"] is False for case in cases))

    def test_group_size_bounds(self):
        with self.assertRaises(ValueError):
            calculator.connected_group(0, 3.0, 0.0, 10_000, 100_000, 10)
        with self.assertRaises(ValueError):
            calculator.connected_group(33, 3.0, 0.0, 10_000, 100_000, 10)


if __name__ == "__main__":
    unittest.main()
