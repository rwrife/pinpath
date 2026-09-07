#include <cstdio>
#include <string>

#include "pico/stdlib.h"

#include "pinpath_core.hpp"

namespace {

class PicoClock : public pinpath::IClock {
 public:
  uint64_t now_ms() const override { return to_ms_since_boot(get_absolute_time()); }
};

class PicoHal : public pinpath::IHal {
 public:
  void enforce_safe_condition() override {
    drive_active_ = false;
    selected_.clear();
  }

  bool safe_condition() const override { return !drive_active_; }

  pinpath::PrecheckStatus run_precheck() override {
    // MVP fail-closed placeholder until analog front-end integration lands.
    return pinpath::PrecheckStatus{false, "precheck_sensor_unavailable"};
  }

  void select_drive_endpoint(const std::string& endpoint) override {
    selected_ = endpoint;
    drive_active_ = true;
  }

  bool sample_edge(const std::string& a, const std::string& b) override {
    (void)a;
    (void)b;
    // Real hardware implementation pending.
    return false;
  }

  void clear_drive() override {
    selected_.clear();
    drive_active_ = false;
  }

  bool unexpected_voltage() const override { return false; }
  bool cancel_requested() const override { return false; }
  bool start_requested() const override { return false; }
  void set_status_fault(bool fault) override { fault_latched_ = fault; }

  void watchdog_kick() override {}

  std::string persistent_hardware_revision() const override {
    return "pinpath-rev-a-candidate";
  }

  std::string persistent_limits_revision() const override { return "limits-rev-a"; }

 private:
  bool drive_active_ = false;
  std::string selected_;
  bool fault_latched_ = false;
};

}  // namespace

int main() {
  stdio_init_all();

  PicoHal hal;
  PicoClock clock;
  pinpath::ProtocolConfig cfg{
      .hardware_revision = "pinpath-rev-a-candidate",
      .firmware_version = "0.1.0-dev",
      .limits_revision = "limits-rev-a",
      .limits_validated = true,
      .adapter_revision = "pinpath-known-loopback-rev-a-candidate",
  };
  pinpath::ProtocolEngine engine(hal, clock, cfg);

  std::string line;
  line.reserve(512);

  while (true) {
    int c = getchar_timeout_us(1000);
    if (c == PICO_ERROR_TIMEOUT) {
      tight_loop_contents();
      continue;
    }

    if (c == '\n') {
      bool has_terminal_cr = !line.empty() && line.back() == '\r';
      if (!line.empty() && !has_terminal_cr) {
        auto frames = engine.handle_line(line);
        for (const auto& frame : frames) {
          auto out = frame.dump();
          printf("%s\n", out.c_str());
        }
      }
      line.clear();
      continue;
    }

    if (line.size() < pinpath::kMaxFrameBytes + 16) {
      line.push_back(static_cast<char>(c));
    }
  }

  return 0;
}
