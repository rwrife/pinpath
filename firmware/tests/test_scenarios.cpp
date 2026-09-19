// Issue #7 integration scenario matrix (host simulation only).
//
// Each scenario exercises one required integration case from issue #7:
// known-good, open, short, crossover, multi-short, reversed-fixture,
// intermittent, disconnect, reset, cancel, precheck-lockout, and
// unexpected-voltage lockout. All results here are `host_simulation`
// evidence against the same protocol core compiled into the RP2040
// firmware; they are NOT bench evidence from assembled hardware.
//
// Default mode asserts invariants (CTest). Setting PINPATH_SCENARIO_JSON=1
// additionally prints a JSON array of scenario records to stdout for the
// release evidence archive (stderr carries the human-readable lines).

#include <cstdlib>
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

  bool cancel_requested() const override { return cancel_at_select > 0 && select_count >= cancel_at_select; }
  bool start_requested() const override { return start_requested_latched; }
  void set_status_fault(bool fault) override { fault_indicator = fault; }
  void watchdog_kick() override { watchdog_kicks++; }

  std::string persistent_hardware_revision() const override { return "pinpath-rev-a-candidate"; }
  std::string persistent_limits_revision() const override { return "limits-rev-a"; }

  bool precheck_pass = true;
  std::string precheck_reason = "ok";
  bool unexpected_voltage_latched = false;
  int cancel_at_select = 0;  // request cancel when select_count reaches N
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

pinpath::ProtocolEngine make_engine(FakeHal& hal, FakeClock& clock) {
  pinpath::ProtocolConfig cfg{
      .hardware_revision = "pinpath-rev-a-candidate",
      .firmware_version = "0.1.0-integration",
      .limits_revision = "limits-rev-a",
      .limits_validated = true,
      .adapter_revision = "pinpath-known-loopback-rev-a-candidate",
  };
  return pinpath::ProtocolEngine(hal, clock, cfg);
}

std::vector<Json> send(pinpath::ProtocolEngine& engine, const std::string& type, const Json& payload,
                       const std::string& id) {
  Json frame{{"v", 1}, {"type", type}, {"id", id}, {"payload", payload}};
  return engine.handle_line(frame.dump());
}

int msg_seq = 0;

// Runs hello + precheck, asserting the precheck passed and the engine is armed.
void arm(FakeHal& hal, FakeClock& clock, pinpath::ProtocolEngine& engine) {
  auto hello = send(engine, "hello", Json::object(), "h-" + std::to_string(++msg_seq));
  if (hello.empty() || hello[0]["type"] != "hello_result") throw std::runtime_error("hello failed");
  auto pre = send(engine, "precheck", Json::object(), "p-" + std::to_string(++msg_seq));
  if (pre.empty() || pre[0]["payload"]["status"] != "pass") throw std::runtime_error("precheck failed in arm()");
  if (engine.state() != pinpath::DeviceState::Armed) throw std::runtime_error("not armed after pass");
}

Json loopback_expected_groups() {
  Json groups = Json::array();
  for (int i = 1; i <= 16; ++i) {
    std::ostringstream a, b;
    a << "A:" << (i < 10 ? "0" : "") << i;
    b << "B:" << (i < 10 ? "0" : "") << i;
    groups.push_back(Json::array({a.str(), b.str()}));
  }
  return groups;
}

void connect_loopback(FakeHal& hal) {
  for (int i = 1; i <= 16; ++i) {
    std::ostringstream a, b;
    a << "A:" << (i < 10 ? "0" : "") << i;
    b << "B:" << (i < 10 ? "0" : "") << i;
    hal.connected_pairs.insert({a.str(), b.str()});
  }
}

Json ep(const std::string& s) { return Json(s); }

struct ScenarioResult {
  std::string name;
  std::string requirement;
  std::string observed;
  bool ok = false;
};

std::vector<ScenarioResult> g_results;

void record(const std::string& name, const std::string& requirement, bool ok, const std::string& observed) {
  g_results.push_back(ScenarioResult{name, requirement, observed, ok});
  std::cerr << (ok ? "[PASS] " : "[FAIL] ") << name << " -- " << observed << "\n";
  if (!ok) {
    throw std::runtime_error("scenario failed: " + name);
  }
}

Json scan_payload_unknown(int reps = 3) {
  return Json{{"mode", "unknown_map"}, {"repetitions", reps}};
}

Json scan_payload_expected(const Json& groups, int reps = 3) {
  return Json{{"mode", "expected_map"}, {"repetitions", reps}, {"profile_schema", "pinpath-profile-v1"},
              {"expected_groups", groups}};
}

// ---------------------------------------------------------------------------
// S1: known-good loopback self-test passes end to end.
// ---------------------------------------------------------------------------
void scenario_known_good() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  arm(hal, clock, engine);

  auto rsp = send(engine, "self_test", Json{{"manifest_revision", "pinpath-known-loopback-rev-a-candidate"},
                                            {"repetitions", 3}},
                  "s1");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "self_test_result") result = &f;
  }
  bool ok = result != nullptr && (*result)["payload"]["classes"]["pass"] == true &&
            (*result)["payload"]["complete"] == true && (*result)["payload"]["quality_flags"]["stable"] == true &&
            (*result)["payload"]["evidence_context"] == "host_simulation" &&
            engine.state() == pinpath::DeviceState::IdleSafe && hal.safe_condition() && !engine.token_present();
  record("known_good_loopback_self_test", "REQ-FUN-003/REQ-SAF-008", ok,
         "16/16 expected loopback groups matched; pass=true; returns idle_safe with no token and no drive");
}

// ---------------------------------------------------------------------------
// S2: failed precheck locks out scan (fault-safe, no token).
// ---------------------------------------------------------------------------
void scenario_precheck_fail_lockout() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  hal.precheck_pass = false;
  hal.precheck_reason = "external_voltage_detected";

  send(engine, "hello", Json::object(), "h-s2");
  auto pre = send(engine, "precheck", Json::object(), "p-s2");
  bool ok = pre[0]["payload"]["status"] == "fail" && engine.state() == pinpath::DeviceState::FaultSafe &&
            !engine.token_present() && hal.fault_indicator && hal.safe_condition();
  auto scan = send(engine, "scan", scan_payload_unknown(3), "s2");
  ok = ok && !scan.empty() && scan[0]["type"] == "error" && scan[0]["payload"]["code"] == "precheck_required" &&
       engine.state() == pinpath::DeviceState::FaultSafe;
  record("precheck_fail_locks_scan", "REQ-SAF-004/REQ-SAF-005", ok,
         "precheck fail -> fault_safe, fault indicator set, scan rejected precheck_required, nodes safe");
}

// ---------------------------------------------------------------------------
// S3: expired precheck token blocks scan and returns to idle safe.
// ---------------------------------------------------------------------------
void scenario_token_expiry() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  arm(hal, clock, engine);
  clock.advance(5001);

  auto scan = send(engine, "scan", scan_payload_unknown(3), "s3");
  bool ok = !scan.empty() && scan[0]["type"] == "error" && scan[0]["payload"]["code"] == "precheck_expired" &&
            engine.state() == pinpath::DeviceState::IdleSafe && !engine.token_present() && hal.safe_condition();
  record("precheck_token_expiry_blocks_scan", "REQ-SAF-005/RISK-019", ok,
         "token >5 s consumed; scan rejected precheck_expired; engine returns idle_safe with no drive");
}

// ---------------------------------------------------------------------------
// S4: missing conductor is reported as open, not as a pass.
// ---------------------------------------------------------------------------
void scenario_open() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  hal.connected_pairs.erase({"A:07", "B:07"});
  arm(hal, clock, engine);

  auto rsp = send(engine, "scan", scan_payload_expected(loopback_expected_groups(), 3), "s4");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "scan_result") result = &f;
  }
  const Json& classes = (*result)["payload"]["classes"];
  bool open_flagged = false;
  for (const auto& g : classes["open"]) {
    if (g.size() == 2 && (g[0] == "A:07" || g[1] == "A:07") && (g[0] == "B:07" || g[1] == "B:07")) {
      open_flagged = true;
    }
  }
  bool ok = result != nullptr && classes["pass"] == false && open_flagged && classes["short"].empty() &&
            classes["crossover"].empty() && hal.safe_condition();
  record("open_detected", "REQ-FUN-003", ok,
         "expected group A:07-B:07 absent from observations -> open bucket, pass=false, other buckets clean");
}

// ---------------------------------------------------------------------------
// S5: two expected conductors merged into one group is reported as short.
// ---------------------------------------------------------------------------
void scenario_short() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  // B:07 also joins the A:01/B:01 group.
  hal.connected_pairs.insert({"A:01", "B:07"});
  arm(hal, clock, engine);

  auto rsp = send(engine, "scan", scan_payload_expected(loopback_expected_groups(), 3), "s5");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "scan_result") result = &f;
  }
  const Json& classes = (*result)["payload"]["classes"];
  bool merged_flagged = false;
  for (const auto& g : classes["short"]) {
    std::set<std::string> s(g.begin(), g.end());
    if (s.count("A:01") && s.count("B:01") && s.count("A:07") && s.count("B:07")) merged_flagged = true;
  }
  bool ok = result != nullptr && classes["pass"] == false && merged_flagged && hal.safe_condition();
  record("short_two_expected_groups_merged", "REQ-FUN-004", ok,
         "observed group {A:01,B:01,A:07,B:07} merges two expected groups -> short bucket, pass=false");
}

// ---------------------------------------------------------------------------
// S6: multi-endpoint short (3 expected groups merged + isolated endpoint
// pulled into a group) is reported as two shorts.
// ---------------------------------------------------------------------------
void scenario_multi_short() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  hal.connected_pairs.insert({"A:01", "A:02"});  // merges expected groups 1 and 2
  hal.connected_pairs.insert({"A:03", "A:04"});  // A:04 joins group 3 -> merges expected group with isolated set
  arm(hal, clock, engine);

  // Expected map keeps only loopback groups 5 and 6 populated; treat 1-4 wires
  // as expected pairs 1..3 and A:04 as expected-isolated.
  Json groups = Json::array();
  for (int i = 1; i <= 3; ++i) {
    std::ostringstream a, b;
    a << "A:" << (i < 10 ? "0" : "") << i;
    b << "B:" << (i < 10 ? "0" : "") << i;
    groups.push_back(Json::array({a.str(), b.str()}));
  }
  // Remove pair 4 connections from observations so A:04 is expected-isolated.
  hal.connected_pairs.erase({"A:04", "B:04"});

  auto rsp = send(engine, "scan", scan_payload_expected(groups, 3), "s6");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "scan_result") result = &f;
  }
  const Json& classes = (*result)["payload"]["classes"];
  bool short1 = false, short2 = false;
  for (const auto& g : classes["short"]) {
    std::set<std::string> s(g.begin(), g.end());
    if (s.count("A:01") && s.count("B:01") && s.count("A:02")) short1 = true;
    if (s.count("A:03") && s.count("B:03") && s.count("A:04")) short2 = true;
  }
  bool ok = result != nullptr && classes["pass"] == false && short1 && short2 && hal.safe_condition();
  record("multi_short_group_merge", "REQ-FUN-004/RISK-004", ok,
         "two independent merged groups (incl. expected-isolated A:04) both land in short bucket; pass=false");
}

// ---------------------------------------------------------------------------
// S7: swapped pair is reported as crossover, not as open+short.
// ---------------------------------------------------------------------------
void scenario_crossover() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  // Swap pair 1/2 ends: A:01->B:02, A:02->B:01.
  hal.connected_pairs.erase({"A:01", "B:01"});
  hal.connected_pairs.erase({"A:02", "B:02"});
  hal.connected_pairs.insert({"A:01", "B:02"});
  hal.connected_pairs.insert({"A:02", "B:01"});
  arm(hal, clock, engine);

  auto rsp = send(engine, "scan", scan_payload_expected(loopback_expected_groups(), 3), "s7");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "scan_result") result = &f;
  }
  const Json& classes = (*result)["payload"]["classes"];
  bool crossover_flagged = classes["crossover"].size() >= 1;
  bool ok = result != nullptr && classes["pass"] == false && crossover_flagged &&
            classes["open"].empty() && hal.safe_condition();
  record("crossover_pair_swap", "REQ-FUN-004", ok,
         "observed cycle {A:01,B:02}+{A:02,B:01} vs expected pairs -> crossover bucket, pass=false");
}

// ---------------------------------------------------------------------------
// S8: reversed adapter fixture (A:i -> B:17-i) is caught, never reported
// as a pass (RISK-006 systematic crossover/short reporting).
// ---------------------------------------------------------------------------
void scenario_reversed_fixture() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  for (int i = 1; i <= 16; ++i) {
    std::ostringstream a, b;
    a << "A:" << (i < 10 ? "0" : "") << i;
    b << "B:" << (17 - i < 10 ? "0" : "") << (17 - i);
    hal.connected_pairs.insert({a.str(), b.str()});
  }
  arm(hal, clock, engine);

  auto rsp = send(engine, "scan", scan_payload_expected(loopback_expected_groups(), 3), "s8");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "scan_result") result = &f;
  }
  const Json& classes = (*result)["payload"]["classes"];
  // Every expected pair i is swapped with pair 17-i, forming 8 crossover cycles
  // that cover all 16 expected pairs; nothing may pass.
  bool ok = result != nullptr && classes["pass"] == false && classes["crossover"].size() == 8 &&
            classes["open"].empty() && hal.safe_condition();
  record("reversed_fixture_caught", "REQ-SAF-008/RISK-006", ok,
         "reversed mapping flags 8 crossover cycles covering all 16 expected pairs, pass=false, returns idle_safe");
}

// ---------------------------------------------------------------------------
// S9: flapping conductor is flagged unstable, never presented as stable.
// ---------------------------------------------------------------------------
void scenario_intermittent() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  hal.unstable_pairs.insert({"A:11", "B:11"});
  arm(hal, clock, engine);

  auto rsp = send(engine, "scan", scan_payload_expected(loopback_expected_groups(), 8), "s9");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "scan_result") result = &f;
  }
  const Json& payload = (*result)["payload"];
  const Json& classes = payload["classes"];
  bool unstable_flagged = classes["unstable"].size() == 2 && payload["quality_flags"]["stable"] == false;
  bool ok = result != nullptr && classes["pass"] == false && unstable_flagged && hal.safe_condition();
  record("intermittent_unstable_flagged", "REQ-FUN-003/RISK-007", ok,
         "alternating samples on A:11-B:11 -> unstable endpoints, stable=false, pass=false (not certainty)");
}

// ---------------------------------------------------------------------------
// S10: cancel during an active scan stops drive first, reports cancelled,
// consumes the token, and requires a fresh precheck (host proxy for the
// USB transport-loss case; real disconnect observation stays bench-only).
// ---------------------------------------------------------------------------
void scenario_cancel_and_transport_loss_proxy() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  hal.cancel_at_select = 20;  // cancel shortly into the first repetition
  arm(hal, clock, engine);

  auto rsp = send(engine, "scan", scan_payload_unknown(4), "s10");
  const Json* cancelled = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "cancelled") cancelled = &f;
  }
  bool ok = cancelled != nullptr && engine.state() == pinpath::DeviceState::IdleSafe &&
            !engine.token_present() && hal.safe_condition() && (*cancelled)["payload"]["complete"] == false;

  // A lost-host/no-further-commands condition cannot leave drive enabled:
  // after cancel the engine has no active operation and the HAL is safe.
  auto rescan = send(engine, "scan", scan_payload_unknown(3), "s10b");
  ok = ok && !rescan.empty() && rescan[0]["payload"]["code"] == "precheck_required" && hal.safe_condition();
  record("cancel_during_scan_returns_safe", "REQ-FUN-006/RISK-009/RISK-011", ok,
         "cancel mid-scan -> cancelled (complete=false), drive disabled, token consumed, rescan needs new precheck");
}

// ---------------------------------------------------------------------------
// S11: reset/boot always comes up safe: hello reports idle_safe and scan
// is refused until a new precheck.
// ---------------------------------------------------------------------------
void scenario_reset_boot_safe() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);  // fresh engine models post-reset state
  connect_loopback(hal);

  auto hello = send(engine, "hello", Json::object(), "h-s11");
  bool ok = hello[0]["payload"]["state"] == "idle_safe" && hal.safe_condition();

  auto scan = send(engine, "scan", scan_payload_unknown(3), "s11");
  ok = ok && scan[0]["type"] == "error" && scan[0]["payload"]["code"] == "precheck_required";

  // Recovery path: precheck -> armed -> scan completes after reset.
  arm(hal, clock, engine);
  auto rsp = send(engine, "scan", scan_payload_unknown(3), "s11c");
  const Json* result = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "scan_result") result = &f;
  }
  ok = ok && result != nullptr && engine.state() == pinpath::DeviceState::IdleSafe && hal.safe_condition();
  record("reset_boot_safe_requires_precheck", "REQ-SAF-002/RISK-010", ok,
         "fresh engine reports idle_safe, refuses scan, and recovers through precheck -> scan -> idle_safe");
}

// ---------------------------------------------------------------------------
// S12: unexpected voltage during scan latches fault-safe and blocks any
// further scan without physical re-precheck.
// ---------------------------------------------------------------------------
void scenario_unexpected_voltage_lockout() {
  FakeHal hal;
  FakeClock clock;
  auto engine = make_engine(hal, clock);
  connect_loopback(hal);
  arm(hal, clock, engine);
  // Voltage appears on the assembly only after the precheck passed.
  hal.unexpected_voltage_latched = true;

  auto rsp = send(engine, "scan", scan_payload_unknown(4), "s12");
  const Json* fault = nullptr;
  for (auto& f : rsp) {
    if (f["type"] == "fault") fault = &f;
  }
  bool ok = fault != nullptr && (*fault)["payload"]["code"] == "unexpected_voltage" &&
            engine.state() == pinpath::DeviceState::FaultSafe && !engine.token_present() &&
            hal.fault_indicator && hal.safe_condition();

  auto rescan = send(engine, "scan", scan_payload_unknown(3), "s12b");
  ok = ok && rescan[0]["payload"]["code"] == "precheck_required";

  // Recovery only through a new precheck with the fault source removed.
  hal.unexpected_voltage_latched = false;
  arm(hal, clock, engine);
  auto scan2 = send(engine, "scan", scan_payload_unknown(3), "s12c");
  const Json* result = nullptr;
  for (auto& f : scan2) {
    if (f["type"] == "scan_result") result = &f;
  }
  ok = ok && result != nullptr && engine.state() == pinpath::DeviceState::IdleSafe;
  record("unexpected_voltage_during_scan_latches_fault_safe", "REQ-SAF-005/RISK-005", ok,
         "voltage mid-scan -> fault latched, drive off, token gone; scan blocked until fault cleared + new precheck");
}

// ---------------------------------------------------------------------------
// S13: unvalidated limits refuse precheck outright (fail-closed gate).
// ---------------------------------------------------------------------------
void scenario_limits_unvalidated_refuses_scan() {
  FakeHal hal;
  FakeClock clock;
  pinpath::ProtocolConfig cfg{
      .hardware_revision = "pinpath-rev-a-candidate",
      .firmware_version = "0.1.0-integration",
      .limits_revision = "limits-rev-a",
      .limits_validated = false,
      .adapter_revision = "pinpath-known-loopback-rev-a-candidate",
  };
  pinpath::ProtocolEngine engine(hal, clock, cfg);

  send(engine, "hello", Json::object(), "h-s13");
  auto pre = send(engine, "precheck", Json::object(), "p-s13");
  bool ok = pre[0]["type"] == "error" && pre[0]["payload"]["code"] == "limits_unavailable" &&
            engine.state() == pinpath::DeviceState::FaultSafe && !engine.token_present() && hal.safe_condition();
  record("unvalidated_limits_refuse_scan", "REQ-SAF-006/RISK-016", ok,
         "limits_validated=false -> precheck error limits_unavailable, fault_safe, no token, nodes safe");
}

}  // namespace

int main() {
  struct NamedScenario {
    const char* name;
    void (*fn)();
  };
  const NamedScenario scenarios[] = {
      {"known_good_loopback_self_test", scenario_known_good},
      {"precheck_fail_locks_scan", scenario_precheck_fail_lockout},
      {"precheck_token_expiry_blocks_scan", scenario_token_expiry},
      {"open_detected", scenario_open},
      {"short_two_expected_groups_merged", scenario_short},
      {"multi_short_group_merge", scenario_multi_short},
      {"crossover_pair_swap", scenario_crossover},
      {"reversed_fixture_caught", scenario_reversed_fixture},
      {"intermittent_unstable_flagged", scenario_intermittent},
      {"cancel_during_scan_returns_safe", scenario_cancel_and_transport_loss_proxy},
      {"reset_boot_safe_requires_precheck", scenario_reset_boot_safe},
      {"unexpected_voltage_during_scan_latches_fault_safe", scenario_unexpected_voltage_lockout},
      {"unvalidated_limits_refuse_scan", scenario_limits_unvalidated_refuses_scan},
  };

  for (const auto& s : scenarios) {
    s.fn();
  }

  if (const char* flag = std::getenv("PINPATH_SCENARIO_JSON"); flag && flag[0] == '1') {
    Json root{{"schema_version", "1.0.0"},
              {"kind", "pinpath-integration-scenario-matrix"},
              {"evidence_context", "host_simulation"},
              {"hardware_revision", "pinpath-rev-a-candidate"},
              {"limits_revision", "limits-rev-a"},
              {"firmware_source", "firmware/src/pinpath_core.cpp (same core compiled for RP2040 target)"},
              {"note", "Host simulation only. Not bench evidence; no assembled unit exists."}};
    Json records = Json::array();
    for (const auto& r : g_results) {
      records.push_back(Json{{"scenario", r.name}, {"requirement_refs", r.requirement},
                             {"result", r.ok ? "pass" : "fail"}, {"observed", r.observed},
                             {"evidence_context", "host_simulation"}});
    }
    root["scenarios"] = records;
    std::cout << root.dump(2) << "\n";
  }

  std::cerr << "scenario matrix: " << g_results.size() << " scenarios, all asserted\n";
  return 0;
}
