#include "pinpath_core.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <map>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <unordered_set>

namespace pinpath {
namespace {

using Json = nlohmann::json;

std::string endpoint_key(const std::vector<std::string>& group) {
  std::ostringstream oss;
  for (size_t i = 0; i < group.size(); ++i) {
    if (i) oss << ",";
    oss << group[i];
  }
  return oss.str();
}

bool is_state_changing_type(const std::string& type) {
  return type == "precheck" || type == "scan" || type == "self_test" || type == "cancel";
}

bool has_duplicate_top_level_keys(const std::string& raw) {
  std::set<std::string> keys;
  int depth = 0;
  bool in_string = false;
  bool escape = false;
  std::string strbuf;
  bool reading_key = false;

  for (size_t i = 0; i < raw.size(); ++i) {
    char c = raw[i];
    if (in_string) {
      if (escape) {
        escape = false;
        if (reading_key) strbuf.push_back(c);
        continue;
      }
      if (c == '\\') {
        escape = true;
        continue;
      }
      if (c == '"') {
        in_string = false;
        if (reading_key && depth == 1) {
          if (keys.count(strbuf)) return true;
          keys.insert(strbuf);
        }
        reading_key = false;
        strbuf.clear();
        continue;
      }
      if (reading_key) strbuf.push_back(c);
      continue;
    }

    if (c == '"') {
      in_string = true;
      if (depth == 1) {
        size_t j = i;
        while (j > 0 && std::isspace(static_cast<unsigned char>(raw[j - 1]))) --j;
        if (j > 0 && (raw[j - 1] == '{' || raw[j - 1] == ',')) {
          reading_key = true;
          strbuf.clear();
        }
      }
      continue;
    }

    if (c == '{' || c == '[') {
      ++depth;
    } else if (c == '}' || c == ']') {
      --depth;
    }
  }
  return false;
}

bool exceeds_depth_limit(const std::string& raw, int max_depth) {
  int depth = 0;
  int peak = 0;
  bool in_string = false;
  bool escape = false;

  for (char c : raw) {
    if (in_string) {
      if (escape) {
        escape = false;
      } else if (c == '\\') {
        escape = true;
      } else if (c == '"') {
        in_string = false;
      }
      continue;
    }

    if (c == '"') {
      in_string = true;
      continue;
    }
    if (c == '{' || c == '[') {
      ++depth;
      peak = std::max(peak, depth);
      if (peak > max_depth) return true;
    } else if (c == '}' || c == ']') {
      --depth;
    }
  }

  return false;
}

std::set<std::string> to_set(const std::vector<std::string>& group) {
  return std::set<std::string>(group.begin(), group.end());
}

bool contains(const std::set<std::string>& s, const std::string& v) {
  return s.find(v) != s.end();
}

}  // namespace

std::vector<std::string> canonical_endpoints() {
  std::vector<std::string> endpoints;
  endpoints.reserve(32);
  for (char bank : {'A', 'B'}) {
    for (int i = 1; i <= 16; ++i) {
      std::ostringstream oss;
      oss << bank << ":";
      if (i < 10) oss << '0';
      oss << i;
      endpoints.push_back(oss.str());
    }
  }
  return endpoints;
}

bool is_valid_endpoint(const std::string& endpoint) {
  if (endpoint.size() != 4) return false;
  if (!(endpoint[0] == 'A' || endpoint[0] == 'B')) return false;
  if (endpoint[1] != ':') return false;
  if (!std::isdigit(static_cast<unsigned char>(endpoint[2])) ||
      !std::isdigit(static_cast<unsigned char>(endpoint[3]))) {
    return false;
  }
  int n = (endpoint[2] - '0') * 10 + (endpoint[3] - '0');
  return n >= 1 && n <= 16;
}

std::string to_string(DeviceState state) {
  switch (state) {
    case DeviceState::BootSafe:
      return "boot_safe";
    case DeviceState::IdleSafe:
      return "idle_safe";
    case DeviceState::Prechecking:
      return "prechecking";
    case DeviceState::Armed:
      return "armed";
    case DeviceState::SelfTesting:
      return "self_testing";
    case DeviceState::Scanning:
      return "scanning";
    case DeviceState::Classifying:
      return "classifying";
    case DeviceState::FaultSafe:
      return "fault_safe";
  }
  return "fault_safe";
}

ProtocolEngine::ProtocolEngine(IHal& hal, IClock& clock, ProtocolConfig cfg)
    : hal_(hal), clock_(clock), cfg_(std::move(cfg)) {
  hal_.enforce_safe_condition();
  state_ = DeviceState::IdleSafe;
}

bool ProtocolEngine::token_present() const { return token_expiry_ms_.has_value(); }

bool ProtocolEngine::token_valid() const {
  if (!token_expiry_ms_.has_value()) return false;
  return clock_.now_ms() <= *token_expiry_ms_;
}

void ProtocolEngine::arm_token() { token_expiry_ms_ = clock_.now_ms() + 5000; }

void ProtocolEngine::consume_token() { token_expiry_ms_.reset(); }

void ProtocolEngine::invalidate_token_and_leave_armed() {
  if (state_ == DeviceState::Armed) {
    token_expiry_ms_.reset();
    state_ = DeviceState::IdleSafe;
  }
}

std::optional<ProtocolEngine::ParseError> ProtocolEngine::parse_json_frame(const std::string& line,
                                                                            Json* out) const {
  if (line.size() > kMaxFrameBytes) {
    return ParseError{"frame_too_large", "frame exceeds 32768 bytes", std::nullopt};
  }
  if (exceeds_depth_limit(line, 8)) {
    return ParseError{"invalid_frame", "JSON nesting exceeds maximum depth", std::nullopt};
  }
  if (has_duplicate_top_level_keys(line)) {
    return ParseError{"invalid_frame", "duplicate top-level JSON keys are not allowed", std::nullopt};
  }

  try {
    *out = Json::parse(line);
  } catch (const std::exception&) {
    return ParseError{"invalid_frame", "malformed JSON frame", std::nullopt};
  }
  return std::nullopt;
}

std::optional<ProtocolEngine::ParseError> ProtocolEngine::validate_common_frame(const Json& frame,
                                                                                 const std::string& raw) const {
  if (!frame.is_object()) {
    return ParseError{"invalid_schema", "frame must be a JSON object", std::nullopt};
  }

  if (!frame.contains("v") || !frame["v"].is_number_integer()) {
    return ParseError{"invalid_schema", "field 'v' must be an integer", std::nullopt};
  }

  if (!frame.contains("type") || !frame["type"].is_string()) {
    return ParseError{"invalid_schema", "field 'type' must be a string", std::nullopt};
  }

  if (!frame.contains("id") || !frame["id"].is_string()) {
    return ParseError{"invalid_schema", "field 'id' must be a string", std::nullopt};
  }

  std::string id = frame["id"].get<std::string>();
  if (id.empty() || id.size() > 64) {
    return ParseError{"invalid_schema", "field 'id' must be 1..64 characters", id};
  }

  if (!frame.contains("payload") || !frame["payload"].is_object()) {
    return ParseError{"invalid_schema", "field 'payload' must be an object", id};
  }

  if (frame["v"].get<int>() != kProtocolMajor) {
    return ParseError{"unsupported_version", "unsupported protocol major", id};
  }

  if (raw.find("\r") != std::string::npos) {
    // Accepted only as a terminal pre-LF sequence in transport layer; inline CR is schema-invalid.
    return ParseError{"invalid_frame", "unexpected carriage return in frame", id};
  }

  return std::nullopt;
}

nlohmann::json ProtocolEngine::error_frame(const std::optional<std::string>& id,
                                           const std::string& code,
                                           const std::string& message,
                                           bool recoverable,
                                           bool invalidate_token_on_armed) {
  if (invalidate_token_on_armed) {
    invalidate_token_and_leave_armed();
  }

  Json payload{{"code", code}, {"message", message}, {"recoverable", recoverable}};
  Json frame{{"v", kProtocolMajor},
             {"type", code == "unexpected_voltage" ? "fault" : "error"},
             {"id", id.value_or("" )},
             {"payload", payload}};
  return frame;
}

Json ProtocolEngine::hello_result(const std::string& id) const {
  Json payload{{"hardware_revision", cfg_.hardware_revision},
               {"firmware_version", cfg_.firmware_version},
               {"protocol_major", kProtocolMajor},
               {"limits_revision", cfg_.limits_revision},
               {"limits_validated", cfg_.limits_validated},
               {"adapter_revision", cfg_.adapter_revision},
               {"capabilities", Json::array({"precheck", "self_test", "unknown_map", "expected_map"})},
               {"state", to_string(state_)}};
  return Json{{"v", kProtocolMajor}, {"type", "hello_result"}, {"id", id}, {"payload", payload}};
}

std::vector<nlohmann::json> ProtocolEngine::handle_precheck(const std::string& id, const Json& payload) {
  (void)payload;
  if (!(state_ == DeviceState::IdleSafe || state_ == DeviceState::FaultSafe)) {
    return {error_frame(id, "invalid_state", "precheck allowed only from idle_safe/fault_safe", true)};
  }

  state_ = DeviceState::Prechecking;
  hal_.enforce_safe_condition();
  if (!hal_.safe_condition()) {
    state_ = DeviceState::FaultSafe;
    consume_token();
    hal_.set_status_fault(true);
    return {error_frame(id, "internal_invariant", "safe condition could not be enforced", false, false)};
  }

  if (!cfg_.limits_validated) {
    state_ = DeviceState::FaultSafe;
    consume_token();
    hal_.set_status_fault(true);
    return {error_frame(id, "limits_unavailable", "limits record is not validated", true, false)};
  }

  if (hal_.persistent_hardware_revision() != cfg_.hardware_revision ||
      hal_.persistent_limits_revision() != cfg_.limits_revision) {
    state_ = DeviceState::FaultSafe;
    consume_token();
    hal_.set_status_fault(true);
    return {error_frame(id, "incompatible_revision",
                        "persistent compatibility metadata does not match runtime config", true,
                        false)};
  }

  PrecheckStatus precheck = hal_.run_precheck();
  Json endpoint_obs = Json::array();
  for (const auto& ep : canonical_endpoints()) {
    endpoint_obs.push_back(Json{{"endpoint", ep}, {"status", "ok"}});
  }

  Json rsp_payload{{"status", precheck.pass ? "pass" : "fail"},
                   {"reason", precheck.reason},
                   {"state", precheck.pass ? "armed" : "fault_safe"},
                   {"hardware_revision", cfg_.hardware_revision},
                   {"limits_revision", cfg_.limits_revision},
                   {"adapter_revision", cfg_.adapter_revision},
                   {"observations", endpoint_obs}};

  if (precheck.pass) {
    state_ = DeviceState::Armed;
    hal_.set_status_fault(false);
    arm_token();
  } else {
    state_ = DeviceState::FaultSafe;
    consume_token();
    hal_.set_status_fault(true);
  }

  return {Json{{"v", kProtocolMajor}, {"type", "precheck_result"}, {"id", id}, {"payload", rsp_payload}}};
}

std::vector<std::vector<std::string>> ProtocolEngine::normalize_groups(const Json& groups,
                                                                        std::optional<ParseError>* err) {
  if (!groups.is_array()) {
    *err = ParseError{"invalid_schema", "expected_groups must be an array", std::nullopt};
    return {};
  }

  std::set<std::string> seen;
  std::vector<std::vector<std::string>> out;
  for (const auto& group_val : groups) {
    if (!group_val.is_array()) {
      *err = ParseError{"invalid_schema", "group must be an array", std::nullopt};
      return {};
    }

    std::set<std::string> members;
    for (const auto& epv : group_val) {
      if (!epv.is_string()) {
        *err = ParseError{"invalid_schema", "endpoint must be a string", std::nullopt};
        return {};
      }
      std::string ep = epv.get<std::string>();
      if (!is_valid_endpoint(ep)) {
        *err = ParseError{"invalid_endpoint", "invalid endpoint in expected_groups", std::nullopt};
        return {};
      }
      if (contains(seen, ep)) {
        *err = ParseError{"duplicate_endpoint", "duplicate endpoint across expected groups", std::nullopt};
        return {};
      }
      members.insert(ep);
    }
    if (members.size() < 2) {
      *err = ParseError{"invalid_schema", "expected groups must contain >=2 endpoints", std::nullopt};
      return {};
    }

    for (const auto& ep : members) seen.insert(ep);
    out.emplace_back(members.begin(), members.end());
  }

  std::sort(out.begin(), out.end(), [](const auto& a, const auto& b) { return a.front() < b.front(); });
  return out;
}

std::vector<std::vector<std::string>> ProtocolEngine::connected_components_from_edges(
    const std::vector<std::string>& endpoints,
    const std::vector<EdgeObs>& edges,
    std::set<std::string>* unstable_endpoints) {
  std::unordered_map<std::string, int> idx;
  for (size_t i = 0; i < endpoints.size(); ++i) idx[endpoints[i]] = static_cast<int>(i);

  std::vector<int> parent(endpoints.size());
  std::iota(parent.begin(), parent.end(), 0);

  auto find = [&](auto self, int x) -> int {
    if (parent[x] == x) return x;
    parent[x] = self(self, parent[x]);
    return parent[x];
  };
  auto unite = [&](int a, int b) {
    int ra = find(find, a);
    int rb = find(find, b);
    if (ra != rb) parent[rb] = ra;
  };

  for (const auto& e : edges) {
    if (e.seen > 0 && e.seen < e.opportunities) {
      unstable_endpoints->insert(e.a);
      unstable_endpoints->insert(e.b);
    }
    if (e.seen == e.opportunities && e.opportunities > 0) {
      unite(idx[e.a], idx[e.b]);
    }
  }

  std::map<int, std::vector<std::string>> groups;
  for (const auto& ep : endpoints) {
    int root = find(find, idx[ep]);
    groups[root].push_back(ep);
  }

  std::vector<std::vector<std::string>> out;
  out.reserve(groups.size());
  for (auto& [_, g] : groups) {
    std::sort(g.begin(), g.end());
    out.push_back(g);
  }
  std::sort(out.begin(), out.end(), [](const auto& a, const auto& b) { return a.front() < b.front(); });
  return out;
}

Json ProtocolEngine::classifier_expected_map(const std::vector<std::vector<std::string>>& expected_groups,
                                             const std::vector<std::vector<std::string>>& observed_groups,
                                             const std::set<std::string>& unstable_endpoints,
                                             bool stable) {
  Json matched = Json::array();
  Json open = Json::array();
  Json shorts = Json::array();
  Json crossovers = Json::array();
  Json unstable = Json::array();

  std::unordered_map<std::string, int> expected_idx;
  for (size_t i = 0; i < expected_groups.size(); ++i) {
    for (const auto& ep : expected_groups[i]) expected_idx[ep] = static_cast<int>(i);
  }

  std::set<std::string> matched_groups;
  std::set<std::string> short_endpoints;
  std::set<std::string> crossover_endpoints;

  std::map<std::string, std::vector<std::string>> observed_by_key;
  for (const auto& g : observed_groups) observed_by_key[endpoint_key(g)] = g;

  for (const auto& eg : expected_groups) {
    std::string k = endpoint_key(eg);
    bool touches_unstable = false;
    for (const auto& ep : eg) {
      if (contains(unstable_endpoints, ep)) {
        touches_unstable = true;
        break;
      }
    }
    if (!touches_unstable && observed_by_key.find(k) != observed_by_key.end()) {
      matched.push_back(eg);
      matched_groups.insert(k);
    }
  }

  // Potential crossover cycles between 2-wire expected groups.
  for (size_t i = 0; i < expected_groups.size(); ++i) {
    if (expected_groups[i].size() != 2) continue;
    for (size_t j = i + 1; j < expected_groups.size(); ++j) {
      if (expected_groups[j].size() != 2) continue;

      std::set<std::string> s;
      s.insert(expected_groups[i].begin(), expected_groups[i].end());
      s.insert(expected_groups[j].begin(), expected_groups[j].end());

      std::vector<std::vector<std::string>> obs_sub;
      for (const auto& og : observed_groups) {
        if (og.size() != 2) continue;
        if (s.count(og[0]) && s.count(og[1])) obs_sub.push_back(og);
      }

      if (obs_sub.size() != 2) continue;
      std::set<std::string> cover;
      for (const auto& og : obs_sub) {
        cover.insert(og[0]);
        cover.insert(og[1]);
      }
      if (cover != s) continue;

      if (endpoint_key(obs_sub[0]) == endpoint_key(expected_groups[i]) ||
          endpoint_key(obs_sub[0]) == endpoint_key(expected_groups[j]) ||
          endpoint_key(obs_sub[1]) == endpoint_key(expected_groups[i]) ||
          endpoint_key(obs_sub[1]) == endpoint_key(expected_groups[j])) {
        continue;
      }

      bool unstable_cycle = false;
      for (const auto& ep : s) {
        if (contains(unstable_endpoints, ep)) unstable_cycle = true;
      }
      if (unstable_cycle) continue;

      Json cycle = Json::array();
      cycle.push_back(obs_sub[0]);
      cycle.push_back(obs_sub[1]);
      crossovers.push_back(cycle);
      crossover_endpoints.insert(s.begin(), s.end());
    }
  }

  // Short detection: observed groups that merge expected groups or include expected-isolated endpoint.
  for (const auto& og : observed_groups) {
    if (og.size() < 2) continue;
    std::set<int> buckets;
    bool includes_isolated = false;

    for (const auto& ep : og) {
      auto it = expected_idx.find(ep);
      if (it == expected_idx.end()) {
        includes_isolated = true;
      } else {
        buckets.insert(it->second);
      }
    }

    bool is_short = false;
    if (includes_isolated && og.size() > 1) is_short = true;
    if (buckets.size() > 1) is_short = true;
    if (og.size() > 2) is_short = true;

    if (is_short) {
      bool crossover_only = true;
      for (const auto& ep : og) {
        if (!contains(crossover_endpoints, ep)) {
          crossover_only = false;
          break;
        }
      }
      if (!crossover_only) {
        shorts.push_back(og);
        short_endpoints.insert(og.begin(), og.end());
      }
    }
  }

  for (const auto& ep : unstable_endpoints) unstable.push_back(ep);

  for (const auto& eg : expected_groups) {
    std::string k = endpoint_key(eg);
    bool skip = matched_groups.count(k) > 0;
    if (!skip) {
      bool all_in_crossover = true;
      bool any_unstable = false;
      bool any_short = false;
      for (const auto& ep : eg) {
        if (!contains(crossover_endpoints, ep)) all_in_crossover = false;
        if (contains(unstable_endpoints, ep)) any_unstable = true;
        if (contains(short_endpoints, ep)) any_short = true;
      }
      if (all_in_crossover || any_unstable || any_short) skip = true;
    }
    if (!skip) open.push_back(eg);
  }

  Json result{{"matched", matched},
              {"open", open},
              {"short", shorts},
              {"crossover", crossovers},
              {"unstable", unstable},
              {"not_evaluated", Json::array()}};

  result["pass"] = stable && matched.size() == expected_groups.size() && open.empty() && shorts.empty() &&
                   crossovers.empty() && unstable.empty();
  return result;
}

std::vector<nlohmann::json> ProtocolEngine::handle_scan(const std::string& id, const Json& payload) {
  if (state_ != DeviceState::Armed) {
    return {error_frame(id, "precheck_required", "scan requires armed state", true)};
  }

  if (!token_valid()) {
    consume_token();
    state_ = DeviceState::IdleSafe;
    return {error_frame(id, "precheck_expired", "precheck token expired", true, false)};
  }

  if (!payload.contains("mode") || !payload["mode"].is_string()) {
    return {error_frame(id, "invalid_schema", "scan mode is required", true)};
  }

  std::string mode = payload["mode"].get<std::string>();
  if (!(mode == "unknown_map" || mode == "expected_map")) {
    return {error_frame(id, "invalid_schema", "mode must be unknown_map or expected_map", true)};
  }

  int repetitions = kDefaultRepetitions;
  if (payload.contains("repetitions")) {
    if (!payload["repetitions"].is_number_integer()) {
      return {error_frame(id, "invalid_schema", "repetitions must be an integer", true)};
    }
    repetitions = payload["repetitions"].get<int>();
  }
  if (repetitions < kMinRepetitions || repetitions > kMaxRepetitions) {
    return {error_frame(id, "invalid_schema", "repetitions out of range", true)};
  }

  std::vector<std::vector<std::string>> expected_groups;
  if (mode == "expected_map") {
    if (!payload.contains("profile_schema") || !payload["profile_schema"].is_string()) {
      return {error_frame(id, "invalid_schema", "profile_schema required for expected_map", true)};
    }
    if (!payload.contains("expected_groups")) {
      return {error_frame(id, "invalid_schema", "expected_groups required for expected_map", true)};
    }
    std::optional<ParseError> gerr;
    expected_groups = normalize_groups(payload["expected_groups"], &gerr);
    if (gerr.has_value()) {
      return {error_frame(id, gerr->code, gerr->message, true)};
    }
  }

  state_ = DeviceState::Scanning;
  std::vector<Json> out;
  out.push_back(Json{{"v", kProtocolMajor},
                     {"type", "progress"},
                     {"id", id},
                     {"payload", Json{{"phase", "scanning"}, {"completed", 0}, {"total", repetitions}}}});

  const auto endpoints = canonical_endpoints();
  std::map<std::pair<std::string, std::string>, int> seen;
  std::map<std::pair<std::string, std::string>, int> opportunities;

  auto key_pair = [](const std::string& a, const std::string& b) {
    return a < b ? std::make_pair(a, b) : std::make_pair(b, a);
  };

  for (int rep = 0; rep < repetitions; ++rep) {
    hal_.watchdog_kick();
    for (size_t i = 0; i < endpoints.size(); ++i) {
      hal_.select_drive_endpoint(endpoints[i]);
      for (size_t j = i + 1; j < endpoints.size(); ++j) {
        auto k = key_pair(endpoints[i], endpoints[j]);
        opportunities[k] += 1;
        if (hal_.sample_edge(endpoints[i], endpoints[j])) seen[k] += 1;
      }
      hal_.clear_drive();

      if (hal_.cancel_requested()) {
        hal_.enforce_safe_condition();
        consume_token();
        state_ = DeviceState::IdleSafe;
        hal_.set_status_fault(false);
        return {Json{{"v", kProtocolMajor},
                     {"type", "cancelled"},
                     {"id", id},
                     {"payload", Json{{"complete", false},
                                       {"state", "idle_safe"},
                                       {"reason", "cancelled"},
                                       {"requested_repetitions", repetitions},
                                       {"completed_repetitions", rep}}}}};
      }
    }

    if (hal_.unexpected_voltage()) {
      hal_.enforce_safe_condition();
      state_ = DeviceState::FaultSafe;
      consume_token();
      hal_.set_status_fault(true);
      return {error_frame(id, "unexpected_voltage", "unexpected voltage detected", false, false)};
    }

    out.push_back(Json{{"v", kProtocolMajor},
                       {"type", "progress"},
                       {"id", id},
                       {"payload", Json{{"phase", "scanning"}, {"completed", rep + 1}, {"total", repetitions}}}});
  }

  state_ = DeviceState::Classifying;

  std::vector<EdgeObs> edge_obs;
  edge_obs.reserve(opportunities.size());
  for (const auto& [k, opp] : opportunities) {
    int hit = seen[k];
    edge_obs.push_back(EdgeObs{k.first, k.second, hit, opp});
  }
  std::sort(edge_obs.begin(), edge_obs.end(), [](const auto& lhs, const auto& rhs) {
    return std::tie(lhs.a, lhs.b) < std::tie(rhs.a, rhs.b);
  });

  std::set<std::string> unstable_endpoints;
  auto observed_groups = connected_components_from_edges(endpoints, edge_obs, &unstable_endpoints);

  bool stable = unstable_endpoints.empty();
  Json classes = Json{{"matched", Json::array()},
                      {"open", Json::array()},
                      {"short", Json::array()},
                      {"crossover", Json::array()},
                      {"unstable", Json::array()},
                      {"not_evaluated", Json::array()},
                      {"pass", false}};

  if (mode == "expected_map") {
    classes = classifier_expected_map(expected_groups, observed_groups, unstable_endpoints, stable);
  }

  Json edge_json = Json::array();
  for (const auto& e : edge_obs) {
    edge_json.push_back(Json{{"a", e.a}, {"b", e.b}, {"seen", e.seen}, {"opportunities", e.opportunities}});
  }

  Json qf{{"precheck_passed", true},
          {"self_test_passed", mode == "expected_map" ? classes["pass"].get<bool>() : false},
          {"complete", true},
          {"stable", stable},
          {"limits_validated", cfg_.limits_validated},
          {"revision_compatible", true}};

  Json result_payload{{"mode", mode},
                      {"requested_repetitions", repetitions},
                      {"completed_repetitions", repetitions},
                      {"state", "idle_safe"},
                      {"complete", true},
                      {"quality_flags", qf},
                      {"hardware_revision", cfg_.hardware_revision},
                      {"firmware_version", cfg_.firmware_version},
                      {"protocol_major", kProtocolMajor},
                      {"limits_revision", cfg_.limits_revision},
                      {"adapter_revision", cfg_.adapter_revision},
                      {"observed_groups", observed_groups},
                      {"edges", edge_json},
                      {"classes", classes},
                      {"evidence_context", "host_simulation"}};

  if (mode == "expected_map") {
    result_payload["expected_groups"] = expected_groups;
  }

  consume_token();
  state_ = DeviceState::IdleSafe;
  hal_.enforce_safe_condition();
  hal_.set_status_fault(false);

  out.push_back(Json{{"v", kProtocolMajor}, {"type", "scan_result"}, {"id", id}, {"payload", result_payload}});
  return out;
}

std::vector<nlohmann::json> ProtocolEngine::handle_self_test(const std::string& id, const Json& payload) {
  if (!payload.contains("manifest_revision") || !payload["manifest_revision"].is_string()) {
    return {error_frame(id, "invalid_schema", "manifest_revision required for self_test", true)};
  }

  if (cfg_.adapter_revision != payload["manifest_revision"].get<std::string>()) {
    return {error_frame(id, "incompatible_revision", "self-test manifest incompatible", true)};
  }

  Json scan_payload{{"mode", "expected_map"},
                    {"repetitions", payload.value("repetitions", kDefaultRepetitions)},
                    {"profile_schema", "pinpath-loopback-v1"}};

  Json groups = Json::array();
  for (int i = 1; i <= 16; ++i) {
    std::ostringstream a;
    std::ostringstream b;
    a << "A:" << (i < 10 ? "0" : "") << i;
    b << "B:" << (i < 10 ? "0" : "") << i;
    groups.push_back(Json::array({a.str(), b.str()}));
  }
  scan_payload["expected_groups"] = groups;

  auto frames = handle_scan(id, scan_payload);
  for (auto& frame : frames) {
    if (frame["type"] == "scan_result") {
      frame["type"] = "self_test_result";
      frame["payload"]["mode"] = "self_test";
    }
  }
  return frames;
}

std::vector<nlohmann::json> ProtocolEngine::handle_cancel(const std::string& id) {
  if (!(state_ == DeviceState::Prechecking || state_ == DeviceState::Scanning ||
        state_ == DeviceState::Classifying || state_ == DeviceState::SelfTesting)) {
    return {error_frame(id, "invalid_state", "cancel requires an active operation", true)};
  }
  hal_.enforce_safe_condition();
  consume_token();
  state_ = DeviceState::IdleSafe;
  hal_.set_status_fault(false);
  return {Json{{"v", kProtocolMajor},
               {"type", "cancelled"},
               {"id", id},
               {"payload", Json{{"complete", false}, {"state", "idle_safe"}, {"reason", "cancelled"}}}}};
}

std::vector<nlohmann::json> ProtocolEngine::handle_line(const std::string& line) {
  Json frame;
  if (auto parse_err = parse_json_frame(line, &frame); parse_err.has_value()) {
    return {error_frame(parse_err->id, parse_err->code, parse_err->message, true)};
  }

  if (auto common_err = validate_common_frame(frame, line); common_err.has_value()) {
    return {error_frame(common_err->id, common_err->code, common_err->message, true)};
  }

  std::string id = frame["id"].get<std::string>();
  std::string type = frame["type"].get<std::string>();

  if (used_ids_.find(id) != used_ids_.end()) {
    return {error_frame(id, "duplicate_id", "request id already used in this session", true)};
  }
  used_ids_.insert(id);

  if (type == "hello") {
    return {hello_result(id)};
  }
  if (type == "precheck") {
    return handle_precheck(id, frame["payload"]);
  }
  if (type == "scan") {
    return handle_scan(id, frame["payload"]);
  }
  if (type == "self_test") {
    return handle_self_test(id, frame["payload"]);
  }
  if (type == "cancel") {
    return handle_cancel(id);
  }

  if (is_state_changing_type(type)) {
    return {error_frame(id, "invalid_state", "unsupported state-changing command", true)};
  }
  return {error_frame(id, "invalid_schema", "unknown message type", true, false)};
}

}  // namespace pinpath
