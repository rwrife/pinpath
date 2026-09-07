#include <cassert>
#include <cstdint>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "nlohmann/json.hpp"
#include "pinpath_core.hpp"

using Json = nlohmann::json;

namespace {

std::pair<std::string, std::string> norm_pair(const std::string& a, const std::string& b) {
  return a < b ? std::make_pair(a, b) : std::make_pair(b, a);
}

class FakeClock : public pinpath::IClock {
 public:
  uint64_t now_ms() const override { return now_ms_; }
  void advance(uint64_t delta_ms) { now_ms_ += delta_ms; }

 private:
  uint64_t now_ms_ = 0;
};

class FakeHal : public pinpath::IHal {
 public:
  void enforce_safe_condition() override {
    drive_active_ = false;
    selected_.clear();
    safe_enforced_count++;
  }

  bool safe_condition() const override { return !drive_active_; }

  pinpath::PrecheckStatus run_precheck() override {
    return pinpath::PrecheckStatus{precheck_pass, precheck_reason};
  }

  void select_drive_endpoint(const std::string& endpoint) override {
    if (drive_active_) {
      throw std::runtime_error("drive already active");
    }
    drive_active_ = true;
    selected_ = endpoint;
    select_count++;
  }

  bool sample_edge(const std::string& a, const std::string& b) override {
    if (!drive_active_) {
      throw std::runtime_error("sample_edge called with no active drive");
    }
    auto k = norm_pair(a, b);
    sample_count[k]++;

    if (unstable_pairs.count(k)) {
      int c = sample_count[k];
      return (c % 2) == 0;
    }

    return connected_pairs.count(k) != 0;
  }

  void clear_drive() override {
    drive_active_ = false;
    selected_.clear();
    clear_count++;
  }

  bool unexpected_voltage() const override { return unexpected_voltage_latched; }
  bool cancel_requested() const override { return cancel_requested_latched; }
  bool start_requested() const override { return start_requested_latched; }
  void set_status_fault(bool fault) override { fault_indicator = fault; }

  void watchdog_kick() override { watchdog_kicks++; }

  std::string persistent_hardware_revision() const override {
    return "pinpath-rev-a-candidate";
  }

  std::string persistent_limits_revision() const override { return "limits-rev-a"; }

  bool precheck_pass = true;
  std::string precheck_reason = "ok";
  bool unexpected_voltage_latched = false;
  bool cancel_requested_latched = false;
  bool start_requested_latched = false;
  bool fault_indicator = false;
  std::set<std::pair<std::string, std::string>> connected_pairs;
  std::set<std::pair<std::string, std::string>> unstable_pairs;
  std::map<std::pair<std::string, std::string>, int> sample_count;
  int safe_enforced_count = 0;
  int select_count = 0;
  int clear_count = 0;
  int watchdog_kicks = 0;

 private:
  bool drive_active_ = false;
  std::string selected_;
};

std::vector<Json> handle(pinpath::ProtocolEngine& engine, const Json& frame) {
  return engine.handle_line(frame.dump());
}

std::vector<Json> handle_raw(pinpath::ProtocolEngine& engine, const std::string& raw) {
  return engine.handle_line(raw);
}

pinpath::ProtocolEngine make_engine(FakeHal& hal, FakeClock& clock) {
  pinpath::ProtocolConfig cfg{
      .hardware_revision = "pinpath-rev-a-candidate",
      .firmware_version = "0.1.0-test",
      .limits_revision = "limits-rev-a",
      .limits_validated = true,
      .adapter_revision = "pinpath-known-loopback-rev-a-candidate",
  };
  return pinpath::ProtocolEngine(hal, clock, cfg);
}

void test_hello() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto rsp = handle(engine, Json{{"v", 1}, {"type", "hello"}, {"id", "h1"}, {"payload", Json::object()}});
  assert(rsp.size() == 1);
  assert(rsp[0]["type"] == "hello_result");
  assert(rsp[0]["payload"]["state"] == "idle_safe");
}

void test_scan_requires_precheck() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto rsp = handle(engine, Json{{"v", 1},
                                 {"type", "scan"},
                                 {"id", "s1"},
                                 {"payload", Json{{"mode", "unknown_map"}}}});
  assert(rsp.size() == 1);
  assert(rsp[0]["type"] == "error");
  assert(rsp[0]["payload"]["code"] == "precheck_required");
}

void test_precheck_pass_and_token_expiry() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p1"}, {"payload", Json::object()}});
  assert(pre[0]["type"] == "precheck_result");
  assert(pre[0]["payload"]["status"] == "pass");
  assert(engine.state() == pinpath::DeviceState::Armed);
  assert(engine.token_present());

  clock.advance(6000);
  auto scan = handle(engine, Json{{"v", 1},
                                  {"type", "scan"},
                                  {"id", "s2"},
                                  {"payload", Json{{"mode", "unknown_map"}}}});
  assert(scan[0]["type"] == "error");
  assert(scan[0]["payload"]["code"] == "precheck_expired");
  assert(engine.state() == pinpath::DeviceState::IdleSafe);
}

void test_duplicate_id_rejected() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto one = handle(engine, Json{{"v", 1}, {"type", "hello"}, {"id", "dup"}, {"payload", Json::object()}});
  assert(one[0]["type"] == "hello_result");
  auto two = handle(engine, Json{{"v", 1}, {"type", "hello"}, {"id", "dup"}, {"payload", Json::object()}});
  assert(two[0]["type"] == "error");
  assert(two[0]["payload"]["code"] == "duplicate_id");
}

void test_malformed_and_oversized_frames() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto malformed = handle_raw(engine, "{\"v\":1,\"type\":\"hello\"");
  assert(malformed[0]["payload"]["code"] == "invalid_frame");

  std::string big(pinpath::kMaxFrameBytes + 10, 'a');
  auto oversized = handle_raw(engine, big);
  assert(oversized[0]["payload"]["code"] == "frame_too_large");
}

void test_duplicate_top_level_keys_rejected() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  std::string raw = "{\"v\":1,\"type\":\"hello\",\"id\":\"k1\",\"payload\":{},\"id\":\"k2\"}";
  auto rsp = handle_raw(engine, raw);
  assert(rsp[0]["payload"]["code"] == "invalid_frame");
}

void test_unknown_map_scan_and_one_drive_at_a_time() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  // Make one stable edge and one unstable edge.
  hal.connected_pairs.insert(norm_pair("A:01", "B:01"));
  hal.unstable_pairs.insert(norm_pair("A:02", "B:02"));

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p2"}, {"payload", Json::object()}});
  assert(pre[0]["payload"]["status"] == "pass");

  auto scan = handle(engine, Json{{"v", 1},
                                  {"type", "scan"},
                                  {"id", "s3"},
                                  {"payload", Json{{"mode", "unknown_map"}, {"repetitions", 4}}}});

  assert(scan.size() >= 2);
  assert(scan.back()["type"] == "scan_result");
  assert(scan.back()["payload"]["quality_flags"]["complete"] == true);
  assert(scan.back()["payload"]["quality_flags"]["stable"] == false);
  assert(hal.select_count == hal.clear_count);
  assert(engine.state() == pinpath::DeviceState::IdleSafe);
  assert(!engine.token_present());
}

void test_expected_map_classification_crossover() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  hal.connected_pairs.insert(norm_pair("A:01", "B:02"));
  hal.connected_pairs.insert(norm_pair("A:02", "B:01"));

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p3"}, {"payload", Json::object()}});
  assert(pre[0]["payload"]["status"] == "pass");

  Json expected = Json::array({Json::array({"A:01", "B:01"}), Json::array({"A:02", "B:02"})});
  auto scan = handle(engine, Json{{"v", 1},
                                  {"type", "scan"},
                                  {"id", "s4"},
                                  {"payload",
                                   Json{{"mode", "expected_map"},
                                        {"repetitions", 4},
                                        {"profile_schema", "pinpath-profile-v1"},
                                        {"expected_groups", expected}}}});

  auto result = scan.back();
  assert(result["type"] == "scan_result");
  assert(result["payload"]["classes"]["crossover"].size() >= 1);
  assert(result["payload"]["classes"]["pass"] == false);
}

void test_self_test_manifest_gate() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p4"}, {"payload", Json::object()}});
  assert(pre[0]["payload"]["status"] == "pass");

  auto bad = handle(engine, Json{{"v", 1},
                                 {"type", "self_test"},
                                 {"id", "st1"},
                                 {"payload", Json{{"manifest_revision", "wrong-rev"}}}});
  assert(bad[0]["type"] == "error");
  assert(bad[0]["payload"]["code"] == "incompatible_revision");
}

void test_invalid_state_change_while_armed_invalidates_token() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p5"}, {"payload", Json::object()}});
  assert(pre[0]["payload"]["status"] == "pass");
  assert(engine.state() == pinpath::DeviceState::Armed);

  auto bad = handle(engine, Json{{"v", 1},
                                 {"type", "scan"},
                                 {"id", "s5"},
                                 {"payload", Json{{"mode", "unknown_map"}, {"repetitions", 1}}}});
  assert(bad[0]["type"] == "error");
  assert(engine.state() == pinpath::DeviceState::IdleSafe);
  assert(!engine.token_present());
}

void test_precheck_rejects_incompatible_persistent_revisions() {
  class MismatchHal : public FakeHal {
   public:
    std::string persistent_hardware_revision() const override { return "other-hw-rev"; }
  } hal;

  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p5b"}, {"payload", Json::object()}});
  assert(pre[0]["type"] == "error");
  assert(pre[0]["payload"]["code"] == "incompatible_revision");
  assert(engine.state() == pinpath::DeviceState::FaultSafe);
}

void test_unexpected_voltage_latches_fault_safe() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p6"}, {"payload", Json::object()}});
  assert(pre[0]["payload"]["status"] == "pass");

  hal.unexpected_voltage_latched = true;
  auto scan = handle(engine, Json{{"v", 1},
                                  {"type", "scan"},
                                  {"id", "s6"},
                                  {"payload", Json{{"mode", "unknown_map"}, {"repetitions", 3}}}});

  assert(scan.size() == 1);
  assert(scan[0]["type"] == "fault");
  assert(scan[0]["payload"]["code"] == "unexpected_voltage");
  assert(engine.state() == pinpath::DeviceState::FaultSafe);
  assert(hal.fault_indicator);
}

void test_cancel_during_scan_returns_safe() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);

  auto pre = handle(engine, Json{{"v", 1}, {"type", "precheck"}, {"id", "p7"}, {"payload", Json::object()}});
  assert(pre[0]["payload"]["status"] == "pass");

  // Trigger cancellation after the first drive-selection block.
  hal.cancel_requested_latched = true;
  auto scan = handle(engine, Json{{"v", 1},
                                  {"type", "scan"},
                                  {"id", "s7"},
                                  {"payload", Json{{"mode", "unknown_map"}, {"repetitions", 3}}}});

  assert(scan.size() == 1);
  assert(scan[0]["type"] == "cancelled");
  assert(scan[0]["payload"]["state"] == "idle_safe");
  assert(engine.state() == pinpath::DeviceState::IdleSafe);
  assert(!engine.token_present());
  assert(!hal.fault_indicator);
}

void run_test(const char* name, const std::function<void()>& fn) {
  try {
    fn();
    std::cout << "[PASS] " << name << "\n";
  } catch (const std::exception& ex) {
    std::cerr << "[FAIL] " << name << ": " << ex.what() << "\n";
    std::exit(1);
  } catch (...) {
    std::cerr << "[FAIL] " << name << ": unknown exception\n";
    std::exit(1);
  }
}

}  // namespace

int main() {
  run_test("hello", test_hello);
  run_test("scan_requires_precheck", test_scan_requires_precheck);
  run_test("precheck_token_expiry", test_precheck_pass_and_token_expiry);
  run_test("duplicate_id", test_duplicate_id_rejected);
  run_test("malformed_oversized", test_malformed_and_oversized_frames);
  run_test("duplicate_top_level_keys", test_duplicate_top_level_keys_rejected);
  run_test("unknown_map_and_drive_cardinality", test_unknown_map_scan_and_one_drive_at_a_time);
  run_test("expected_map_crossover", test_expected_map_classification_crossover);
  run_test("self_test_manifest_gate", test_self_test_manifest_gate);
  run_test("armed_invalidation", test_invalid_state_change_while_armed_invalidates_token);
  run_test("persistent_revision_gate", test_precheck_rejects_incompatible_persistent_revisions);
  run_test("unexpected_voltage_fault", test_unexpected_voltage_latches_fault_safe);
  run_test("cancel_returns_safe", test_cancel_during_scan_returns_safe);

  std::cout << "All tests passed\n";
  return 0;
}
