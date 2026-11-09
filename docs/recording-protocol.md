# Recording real motion to re-tune the fall threshold (issue #9)

Issue: [#9 Develop fall classification ML model](https://github.com/akhnafyooga/JagSi/issues/9)

Week 6 showed the stored threshold of 0.11 flags normal walking as a fall, but the
test used synthetic windows, so it cannot tell us the right threshold. This protocol
collects the real data that can.

## Safety first

- **Falls are only ever done onto a thick mattress, by a young, healthy team
  member, with a second person watching.** Never by an elderly person.
- Stop if anyone feels pain or dizziness.
- Wear the watch on the wrist the way the product will be worn, and write down
  which wrist in the session note.

## What to record

One session per activity. For falls, **one fall per session**: start recording,
stand still for about 5 s, fall, lie still for about 5 s, stop.

| Activity label | How | Per person |
|----------------|-----|------------|
| `still` | sit or stand normally | 2 min |
| `walking` | normal pace, indoor | 3 min |
| `stairs` | up and down a flight of stairs | 2 min |
| `sit_to_stand` | stand up from a chair, sit back, repeat | 2 min |
| `sit_down_hard` | drop onto a chair or sofa on purpose | 1 min |
| `lie_down` | lie down on a bed deliberately, get up, repeat | 1 min |
| `fall_forward` | one fall forward onto the mattress | 4 sessions |
| `fall_backward` | one fall backward onto the mattress | 3 sessions |
| `fall_side` | one fall sideways onto the mattress | 3 sessions |

At least **two people**, so the threshold does not fit one person's way of moving.
The re-tune script warns when there are fewer than 10 fall sessions, less than
10 minutes of non-fall movement, or only one person.

`sit_down_hard`, `stairs` and `lie_down` matter most: they are the movements most
likely to look like a fall.

## How

The backend records every motion window the watch sends while a session is open,
over either transport (public broker or Azure IoT Hub).

```bash
API=localhost:8000

# start
curl -X POST $API/api/recording/start -H 'Content-Type: application/json' \
     -d '{"label":"walking","subject":"s01","note":"left wrist"}'

# ... do the activity ...

# stop
curl -X POST $API/api/recording/stop

# what is open right now
curl -s $API/api/recording
```

`subject` is a code (`s01`, `s02`), never a name. Recordings are saved as
`backend/data/recordings/<time>_<subject>_<label>.jsonl` and are not committed.

## Re-tuning

```bash
cd backend
python3 scripts/retune_threshold.py --json ../docs/retune-result.json \
        --write-artifact ml/artifacts/fall_clf_retuned.joblib
```

How it scores, and why:

- A fall recording is one **session**: it counts as detected if any of its windows
  reaches the threshold. (Most windows in a fall recording are the standing and
  lying parts, so scoring them one by one would be wrong.)
- Everything else is scored the way the caregiver would experience it: flagged
  windows are grouped by the backend's 15-second cooldown into **alerts**.
- It reports, for the stored threshold and the chosen one: fall recall, alert
  precision, and false alerts per hour.
- It picks the threshold in the **middle** of the range that meets both targets
  (recall >= 0.95 and precision >= 0.90), so precision weighs as much as recall.

It never overwrites `fall_clf.joblib`. The model owner reads the report, then
either swaps in the re-tuned copy or sets `JAGSI_FALL_THRESHOLD`, and updates
`ml/model_card.md` with the operating point and the activities it was tested on.
