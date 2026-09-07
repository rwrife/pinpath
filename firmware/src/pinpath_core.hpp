#pragma once

#include <cstdint>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

namespace pinpath {

inline constexpr int kProtocolMajor = 1;
inline constexpr size_t kMaxFrameBytes = 32768;
inline constexpr int kDefaultRepetitions = 8;
inline constexpr int kMinRepetitions = 3;
inline constexpr int kMaxRepetitions = 64;

std::vector<std::string> canonical_endpoints();
bool is_valid_endpoint(const std::string& endpoint);

enum class DeviceState {
  BootSafe,
  IdleSafe,
  Prechecking,
  Armed,
  SelfTesting,
  Scanning,
  Classifying,
  FaultSafe,
};

std::string to_string(DeviceState state);

struct PrecheckStatus {
  bool pass;
  std::string reason;
};

class IClock {
 public:
  virtual ~IClock() = default;
  virtual uint64_t now_ms() const = 0;
};

class IHal {
 public:
  virtual ~IHal() = default;

  virtual void enforce_safe_condition() = 0;
  virtual bool safe_condition() const = 0;
  virtual PrecheckStatus run_precheck() = 0;
  virtual void select_drive_endpoint(const std::string& endpoint) = 0;
  virtual bool sample_edge(const std::string& a, const std::string& b) = 0;
  virtual void clear_drive() = 0;
  virtual bool unexpected_voltage() const = 0;
  virtual bool cancel_requested() const = 0;
  virtual bool start_requested() const = 0;
  virtual void set_status_fault(bool fault) = 0;
  virtual void watchdog_kick() = 0;

  // Persisted compatibility metadata hooks.
  virtual std::string persistent_hardware_revision() const = 0;
  virtual std::string persistent_limits_revision() const = 0;
};

struct ProtocolConfig {
  std::string hardware_revision;
  std::string firmware_version;
  std::string limits_revision;
  bool limits_validated;
  std::string adapter_revision;  // "none" if unknown
};

class ProtocolEngine {
 public:
  ProtocolEngine(IHal& hal, IClock& clock, ProtocolConfig cfg);

  std::vector<nlohmann::json> handle_line(const std::string& line);

  DeviceState state() const { return state_; }
  bool token_present() const;

 private:
  using Json = nlohmann::json;

  struct ParseError {
    std::string code;
    std::string message;
    std::optional<std::string> id;
  };

  struct EdgeObs {
    std::string a;
    std::string b;
    int seen;
    int opportunities;
  };

  struct ScanOutcome {
    std::vector<std::vector<std::string>> observed_groups;
    std::vector<EdgeObs> edges;
    std::set<std::string> unstable_endpoints;
  };

  std::optional<ParseError> validate_common_frame(const Json& frame, const std::string& raw) const;
  std::optional<ParseError> parse_json_frame(const std::string& line, Json* out) const;

  Json error_frame(const std::optional<std::string>& id,
                   const std::string& code,
                   const std::string& message,
                   bool recoverable,
                   bool invalidate_token_on_armed = true);

  Json hello_result(const std::string& id) const;
  std::vector<Json> handle_precheck(const std::string& id, const Json& payload);
  std::vector<Json> handle_scan(const std::string& id, const Json& payload);
  std::vector<Json> handle_self_test(const std::string& id, const Json& payload);
  std::vector<Json> handle_cancel(const std::string& id);

  bool token_valid() const;
  void arm_token();
  void consume_token();
  void invalidate_token_and_leave_armed();

  static std::vector<std::vector<std::string>> normalize_groups(const Json& groups, std::optional<ParseError>* err);
  static std::vector<std::vector<std::string>> connected_components_from_edges(
      const std::vector<std::string>& endpoints,
      const std::vector<EdgeObs>& edges,
      std::set<std::string>* unstable_endpoints);
  static Json classifier_expected_map(
      const std::vector<std::vector<std::string>>& expected_groups,
      const std::vector<std::vector<std::string>>& observed_groups,
      const std::set<std::string>& unstable_endpoints,
      bool stable);

  IHal& hal_;
  IClock& clock_;
  ProtocolConfig cfg_;
  DeviceState state_ = DeviceState::IdleSafe;
  std::optional<uint64_t> token_expiry_ms_;
  std::set<std::string> used_ids_;
};

}  // namespace pinpath
