/*
 * JagSi - rolling motion window buffer
 *
 * Holds the last N motion samples so the firmware can publish a full window to
 * the fall classifier instead of a single reading. Kept in its own header, with
 * no Arduino dependency, so it compiles and is unit-tested on a normal PC:
 *
 *     g++ -std=c++17 -I firmware/jagsi-watch firmware/test/test_motion_window.cpp -o /tmp/t && /tmp/t
 *
 * Wokwi note: this file must sit in the same sketch folder as sketch.ino. In the
 * Wokwi editor use the "+" tab to add a file named exactly motion_window.h.
 *
 * v0.2 (end product): every slot also remembers how many 10 Hz samples were
 * missed just before it was taken. droppedInWindow() adds up the gaps that sit
 * BETWEEN samples of the current window, so a window that contains a gap stays
 * rejected by the backend until that gap has aged out of the window (30 more
 * clean samples). The old firmware reset its counter after every publish, which
 * let the next two overlapping windows through with the gap still inside them.
 */

#ifndef JAGSI_MOTION_WINDOW_H
#define JAGSI_MOTION_WINDOW_H

#include <stdint.h>

// One motion reading. Units follow backend/ml/schema.py AccelSample:
// accelerometer in g, gyroscope in deg/s.
struct MotionSample {
  float ax = 0, ay = 0, az = 0;
  float gx = 0, gy = 0, gz = 0;
};

// Fixed-size circular buffer of the most recent Capacity samples.
// Capacity must equal WINDOW_SIZE in backend/ml/schema.py (30).
template <uint8_t Capacity>
class MotionWindow {
 public:
  // missedBefore = number of samples that should have been taken between the
  // previous sample and this one but were not (0 for a clean 10 Hz step).
  void push(const MotionSample &s, uint16_t missedBefore = 0) {
    buf_[head_] = s;
    gap_[head_] = missedBefore > 255 ? 255 : (uint8_t)missedBefore;
    head_ = (uint8_t)((head_ + 1) % Capacity);
    if (filled_ < Capacity) filled_++;
  }

  bool full() const { return filled_ >= Capacity; }
  uint8_t filled() const { return filled_; }
  static uint8_t capacity() { return Capacity; }

  // Copies the window into out[Capacity] in chronological order, oldest first.
  // Returns false (and writes nothing) until the buffer has filled once, because
  // a partial window would give the classifier a feature vector it never saw in
  // training. Once full, head_ points at the oldest sample.
  bool snapshot(MotionSample *out) const {
    if (!full()) return false;
    uint8_t idx = head_;
    for (uint8_t i = 0; i < Capacity; i++) {
      out[i] = buf_[idx];
      idx = (uint8_t)((idx + 1) % Capacity);
    }
    return true;
  }

  // Samples missed between consecutive samples of the current window. The gap
  // in front of the oldest sample is outside the window, so it is not counted.
  // Returns 0 for a partial buffer (it is never published anyway).
  uint16_t droppedInWindow() const {
    if (!full()) return 0;
    uint16_t total = 0;
    uint8_t idx = (uint8_t)((head_ + 1) % Capacity);   // second-oldest sample
    for (uint8_t i = 1; i < Capacity; i++) {
      total += gap_[idx];
      idx = (uint8_t)((idx + 1) % Capacity);
    }
    return total;
  }

  void reset() {
    head_ = 0;
    filled_ = 0;
    for (uint8_t i = 0; i < Capacity; i++) gap_[i] = 0;
  }

 private:
  MotionSample buf_[Capacity];
  uint8_t gap_[Capacity] = {0};
  uint8_t head_ = 0;     // next slot to write; also the oldest slot once full
  uint8_t filled_ = 0;   // capped at Capacity
};

#endif  // JAGSI_MOTION_WINDOW_H
