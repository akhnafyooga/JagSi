/*
 * Host-side unit tests for firmware/jagsi-watch/motion_window.h
 *
 * The ring buffer is the one piece of firmware logic that is easy to get wrong
 * and expensive to debug on a simulator: if the samples come out in the wrong
 * order, the classifier still returns a number, it is just the wrong number.
 * These tests pin the ordering down without needing Wokwi.
 *
 * Build and run:
 *     g++ -std=c++17 -Wall -Wextra -I firmware/jagsi-watch \
 *         firmware/test/test_motion_window.cpp -o /tmp/test_motion_window
 *     /tmp/test_motion_window
 */

#include "motion_window.h"

#include <cstdio>
#include <cstdlib>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                       \
  do {                                                         \
    checks++;                                                  \
    if (!(cond)) {                                             \
      failures++;                                              \
      std::printf("  FAIL  %s  (line %d)\n", (msg), __LINE__); \
    }                                                          \
  } while (0)

// Matches WINDOW_SIZE in backend/ml/schema.py
static const uint8_t kWindow = 30;

static MotionSample make(float seed) {
  MotionSample s;
  s.ax = seed;
  s.ay = seed + 0.1f;
  s.az = seed + 0.2f;
  s.gx = seed * 10.0f;
  s.gy = seed * 20.0f;
  s.gz = seed * 30.0f;
  return s;
}

static void test_not_full_until_capacity() {
  std::printf("test_not_full_until_capacity\n");
  MotionWindow<kWindow> w;
  MotionSample out[kWindow];

  CHECK(!w.full(), "empty buffer must not report full");
  CHECK(!w.snapshot(out), "empty buffer must refuse to snapshot");

  for (uint8_t i = 0; i < kWindow - 1; i++) {
    w.push(make((float)i));
    CHECK(!w.full(), "buffer must not report full before capacity");
    CHECK(!w.snapshot(out), "partial window must be refused");
  }

  w.push(make((float)(kWindow - 1)));
  CHECK(w.full(), "buffer must report full at capacity");
  CHECK(w.filled() == kWindow, "filled() must equal capacity");
  CHECK(w.snapshot(out), "full window must be returned");
}

static void test_first_window_is_chronological() {
  std::printf("test_first_window_is_chronological\n");
  MotionWindow<kWindow> w;
  for (uint8_t i = 0; i < kWindow; i++) w.push(make((float)i));

  MotionSample out[kWindow];
  CHECK(w.snapshot(out), "snapshot must succeed");
  bool ordered = true;
  for (uint8_t i = 0; i < kWindow; i++) {
    if (out[i].ax != (float)i) ordered = false;
  }
  CHECK(ordered, "samples 0..29 must come back in that order");
}

static void test_wraparound_keeps_newest_oldest_first() {
  std::printf("test_wraparound_keeps_newest_oldest_first\n");
  MotionWindow<kWindow> w;
  // Push 45 samples into a 30-slot buffer: 0..14 must be discarded.
  for (uint8_t i = 0; i < 45; i++) w.push(make((float)i));

  MotionSample out[kWindow];
  CHECK(w.snapshot(out), "snapshot must succeed after wraparound");
  CHECK(out[0].ax == 15.0f, "oldest retained sample must be 15");
  CHECK(out[kWindow - 1].ax == 44.0f, "newest sample must be last");

  bool ordered = true;
  for (uint8_t i = 0; i < kWindow; i++) {
    if (out[i].ax != (float)(15 + i)) ordered = false;
  }
  CHECK(ordered, "window must be contiguous and chronological after wrap");
}

static void test_all_axes_survive_the_round_trip() {
  std::printf("test_all_axes_survive_the_round_trip\n");
  MotionWindow<kWindow> w;
  for (uint8_t i = 0; i < kWindow; i++) w.push(make((float)i));

  MotionSample out[kWindow];
  w.snapshot(out);
  const MotionSample expected = make(7.0f);
  CHECK(out[7].ax == expected.ax, "ax must be preserved");
  CHECK(out[7].ay == expected.ay, "ay must be preserved");
  CHECK(out[7].az == expected.az, "az must be preserved");
  CHECK(out[7].gx == expected.gx, "gx must be preserved");
  CHECK(out[7].gy == expected.gy, "gy must be preserved");
  CHECK(out[7].gz == expected.gz, "gz must be preserved");
}

static void test_reset_clears_the_window() {
  std::printf("test_reset_clears_the_window\n");
  MotionWindow<kWindow> w;
  for (uint8_t i = 0; i < kWindow; i++) w.push(make((float)i));
  CHECK(w.full(), "precondition: buffer is full");

  w.reset();
  CHECK(!w.full(), "reset must clear the full flag");
  CHECK(w.filled() == 0, "reset must clear the fill count");

  // After reset the buffer must refill from scratch, not resume mid-window.
  for (uint8_t i = 0; i < kWindow; i++) w.push(make((float)(100 + i)));
  MotionSample out[kWindow];
  w.snapshot(out);
  CHECK(out[0].ax == 100.0f, "refill after reset must start at the new oldest");
}

static void test_capacity_matches_ml_schema() {
  std::printf("test_capacity_matches_ml_schema\n");
  // 10 Hz * 3.0 s = 30 samples (backend/ml/schema.py). If the model is
  // retrained at another rate this test is the first thing that should break.
  CHECK(MotionWindow<kWindow>::capacity() == 30, "capacity must be 30 samples");
}

int main() {
  test_not_full_until_capacity();
  test_first_window_is_chronological();
  test_wraparound_keeps_newest_oldest_first();
  test_all_axes_survive_the_round_trip();
  test_reset_clears_the_window();
  test_capacity_matches_ml_schema();

  std::printf("\n%d checks, %d failures\n", checks, failures);
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
