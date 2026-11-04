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
  void push(const MotionSample &s) {
    buf_[head_] = s;
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

  void reset() {
    head_ = 0;
    filled_ = 0;
  }

 private:
  MotionSample buf_[Capacity];
  uint8_t head_ = 0;     // next slot to write; also the oldest slot once full
  uint8_t filled_ = 0;   // capped at Capacity
};

#endif  // JAGSI_MOTION_WINDOW_H
