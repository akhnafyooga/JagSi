// Parses an IoT Hub direct-method topic (issue #8). No Arduino dependencies, so
// firmware/test/test_azure_method.cpp can compile and test it on a normal PC.
//
//   $iothub/methods/POST/<method name>/?$rid=<request id>
//
// IoT Hub generates the request id; the response must echo it on
//   $iothub/methods/res/<status>/?$rid=<request id>
#pragma once

#include <stddef.h>
#include <string.h>

#define AZURE_METHODS_PREFIX "$iothub/methods/POST/"

// Returns false for anything that is not a well-formed method request. On
// success `method` holds the NUL-terminated name and `rid` points into `topic`.
inline bool parseMethodTopic(const char *topic, char *method, size_t methodSize, const char **rid) {
  const size_t prefixLen = strlen(AZURE_METHODS_PREFIX);
  if (!topic || !method || methodSize == 0 || !rid) return false;
  if (strncmp(topic, AZURE_METHODS_PREFIX, prefixLen) != 0) return false;

  const char *name = topic + prefixLen;
  const char *slash = strchr(name, '/');
  if (!slash || slash == name) return false;
  size_t nameLen = (size_t)(slash - name);
  if (nameLen >= methodSize) return false;          // refuse rather than truncate

  const char *r = strstr(slash, "$rid=");
  if (!r || !r[5]) return false;
  r += 5;
  // The id ends at the next '&' if IoT Hub ever appends more properties; keep
  // it NUL-terminated by requiring that it is the last field for now.
  if (strchr(r, '&')) return false;

  memcpy(method, name, nameLen);
  method[nameLen] = '\0';
  *rid = r;
  return true;
}
