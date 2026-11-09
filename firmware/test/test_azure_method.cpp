// Host test for azure_method.h. Run from the repository root:
//   g++ -std=c++17 -Wall -Wextra -I firmware/jagsi-watch firmware/test/test_azure_method.cpp -o /tmp/t
//   /tmp/t
#include <cstdio>
#include <cstring>

#include "azure_method.h"

static int checks = 0, failures = 0;
#define CHECK(cond)                                                   \
  do {                                                                \
    ++checks;                                                         \
    if (!(cond)) {                                                    \
      ++failures;                                                     \
      std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);     \
    }                                                                 \
  } while (0)

static void test_parses_name_and_rid() {
  char m[32];
  const char *rid = nullptr;
  CHECK(parseMethodTopic("$iothub/methods/POST/ack_alert/?$rid=1f", m, sizeof m, &rid));
  CHECK(std::strcmp(m, "ack_alert") == 0);
  CHECK(rid && std::strcmp(rid, "1f") == 0);
  std::puts("test_parses_name_and_rid");
}

static void test_rejects_other_topics() {
  char m[32];
  const char *rid = nullptr;
  CHECK(!parseMethodTopic("jagsi/abal/v1/jagsi-watch-01/cmd", m, sizeof m, &rid));
  CHECK(!parseMethodTopic("$iothub/twin/res/200/?$rid=1", m, sizeof m, &rid));
  CHECK(!parseMethodTopic("$iothub/methods/POST/ping", m, sizeof m, &rid));          // no rid
  CHECK(!parseMethodTopic("$iothub/methods/POST//?$rid=2", m, sizeof m, &rid));      // empty name
  CHECK(!parseMethodTopic("$iothub/methods/POST/ping/?$rid=", m, sizeof m, &rid));   // empty rid
  CHECK(!parseMethodTopic(nullptr, m, sizeof m, &rid));
  std::puts("test_rejects_other_topics");
}

static void test_long_name_is_refused_not_truncated() {
  char m[8];
  const char *rid = nullptr;
  CHECK(!parseMethodTopic("$iothub/methods/POST/set_interval/?$rid=3", m, sizeof m, &rid));
  CHECK(parseMethodTopic("$iothub/methods/POST/ping/?$rid=3", m, sizeof m, &rid));
  std::puts("test_long_name_is_refused_not_truncated");
}

int main() {
  test_parses_name_and_rid();
  test_rejects_other_topics();
  test_long_name_is_refused_not_truncated();
  std::printf("\n%d checks, %d failures\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
