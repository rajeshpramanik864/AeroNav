from __future__ import annotations

import math
import time
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AeroNav Backend", version="2.0.0")
app.state.started_at = time.time()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

state = {
    "mission": "idle", "gps": "denied", "battery": 78.0,
    "position": {"x": 0.0, "y": 0.0, "z": 5.0}, "speed": 0.0, "heading": 45.0,
    "confidence": 94.0, "camera_confidence": 92.0, "imu_confidence": 89.0,
    "ground_confidence": 97.0, "position_error": 0.12,
    "obstacle_injected": False, "failure": None, "path_version": 1,
    "mission_elapsed": 0.0, "battery_start": 78.0, "last_running_at": None,
    "landing_started_at": None, "event": "SYSTEM READY · GPS-DENIED MODE AVAILABLE",
}

class MissionAction(BaseModel):
    action: Literal["start", "pause", "resume", "reroute", "emergency_land"]

class FailureAction(BaseModel):
    failure: Literal["gps_failure", "camera_failure", "communication_loss", "low_battery", "dynamic_obstacle", "sensor_degradation"]


def tick():
    now = time.time()
    if state["mission"] == "running":
        if state["last_running_at"] is None:
            state["last_running_at"] = now
        dt = now - state["last_running_at"]
        state["mission_elapsed"] += max(0.0, dt)
        state["last_running_at"] = now
        t = (state["mission_elapsed"] * 0.055) % 1.0
        state["position"] = {
            "x": round(30 * t, 2),
            "y": round(12 * math.sin(t * math.pi), 2),
            "z": round(5 + 10 * math.sin(t * math.pi / 2), 2),
        }
        state["speed"] = round(2.8 + 0.5 * math.sin(state["mission_elapsed"]), 2)
        state["heading"] = round((45 + t * 100) % 360, 1)
        state["battery"] = max(0.0, round(state["battery_start"] - state["mission_elapsed"] * 0.08, 1))
        state["position_error"] = round(0.08 + 0.05 * abs(math.sin(state["mission_elapsed"])), 3)
        state["confidence"] = round(max(75, 96 - state["position_error"] * 20), 1)
    elif state["mission"] == "landing":
        if state["landing_started_at"] is None:
            state["landing_started_at"] = now
        progress = min(1.0, (now - state["landing_started_at"]) / 4.0)
        state["position"]["z"] = round(max(0.3, 5.0 * (1 - progress)), 2)
        state["speed"] = 0.0
        state["confidence"] = 98.0
        state["event"] = f"PRECISION LANDING · {round(progress * 100)}%"
        if progress >= 1.0:
            state["mission"] = "landed"
            state["position"]["z"] = 0.3
            state["event"] = "LANDED · LANDING PAD VERIFIED"
    return state


def reset_for_start():
    state.update({
        "mission": "running", "battery": 78.0, "battery_start": 78.0,
        "mission_elapsed": 0.0, "last_running_at": time.time(), "landing_started_at": None,
        "failure": None, "obstacle_injected": False, "position": {"x": 0.0, "y": 0.0, "z": 5.0},
        "speed": 2.8, "event": "MISSION STARTED · AUTONOMOUS TAKE-OFF",
    })

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AeroNav Backend", "version": app.version}

@app.get("/api/telemetry")
def telemetry():
    tick()
    return {k: state[k] for k in ["mission", "gps", "battery", "position", "speed", "heading", "position_error", "event"]} | {"uptime": round(time.time() - app.state.started_at, 1), "position_confidence": state["confidence"], "failure": state["failure"]}

@app.post("/api/mission")
def mission(payload: MissionAction):
    action = payload.action
    tick()
    if action == "start":
        reset_for_start()
    elif action == "pause" and state["mission"] == "running":
        tick(); state["mission"] = "paused"; state["last_running_at"] = None; state["speed"] = 0.0; state["event"] = "MISSION PAUSED · BATTERY HOLD"
    elif action == "resume" and state["mission"] == "paused":
        state["mission"] = "running"; state["last_running_at"] = time.time(); state["event"] = "MISSION RESUMED · NAVIGATION CONTINUES"
    elif action == "reroute":
        state["path_version"] += 1; state["obstacle_injected"] = False; state["mission"] = "running"; state["last_running_at"] = time.time(); state["event"] = "PATH REPLANNED · SAFE CORRIDOR UPDATED"
    elif action == "emergency_land":
        state["mission"] = "landing"; state["landing_started_at"] = time.time(); state["last_running_at"] = None; state["speed"] = 0.0; state["event"] = "PRECISION LANDING INITIATED"
    tick()
    return {"ok": True, "action": action, "state": state}

@app.post("/api/simulation/failure")
def simulate_failure(payload: FailureAction):
    failure = payload.failure; state["failure"] = failure
    if failure == "gps_failure":
        state["gps"] = "denied"; state["event"] = "GPS LOSS · SENSOR FUSION ACTIVE"; state["mission"] = "running" if state["mission"] in ["idle", "paused", "gps-denied-autonomy"] else state["mission"]
    elif failure == "camera_failure":
        state["camera_confidence"] = 42.0; state["imu_confidence"] = 94.0; state["ground_confidence"] = 97.0; state["confidence"] = 91.0; state["event"] = "CAMERA DEGRADED · TRUST SHIFTED TO IMU + GROUND"
    elif failure == "communication_loss":
        state["mission"] = "failsafe-return-or-land"; state["last_running_at"] = None; state["speed"] = 0.0; state["event"] = "COMMUNICATION LOSS · FAILSAFE HOLD / LAND"
    elif failure == "low_battery":
        state["battery"] = 15.0; state["battery_start"] = 15.0; state["mission"] = "battery-failsafe"; state["last_running_at"] = None; state["speed"] = 0.0; state["event"] = "LOW BATTERY · SAFE LANDING RECOMMENDED"
    elif failure == "dynamic_obstacle":
        state["obstacle_injected"] = True; state["path_version"] += 1; state["mission"] = "dynamic-reroute"; state["event"] = "DYNAMIC OBSTACLE · REPLANNING REQUIRED"
    elif failure == "sensor_degradation":
        state["camera_confidence"] = 55.0; state["imu_confidence"] = 76.0; state["ground_confidence"] = 95.0; state["confidence"] = 89.0; state["event"] = "SENSOR DEGRADATION · SELF-HEALING FUSION ACTIVE"
    tick()
    return {"ok": True, "failure": failure, "automatic_response": automatic_response(failure), "sensors": sensors()["sensors"], "telemetry": telemetry()}

def automatic_response(failure: str) -> str:
    return {
        "gps_failure": "Switch to GPS-denied localization and sensor fusion",
        "camera_failure": "Reduce camera trust and increase IMU/ground weighting",
        "communication_loss": "Enter communication-loss failsafe and evaluate return/hold/land",
        "low_battery": "Select battery-safe return or nearest safe landing",
        "dynamic_obstacle": "Predict obstacle motion and recalculate 3D path",
        "sensor_degradation": "Reweight sensor fusion and maintain safe corridor",
    }[failure]

@app.get("/api/sensors")
def sensors():
    return {"sensors": {"camera": state["camera_confidence"], "imu": state["imu_confidence"], "ground_tracking": state["ground_confidence"], "gps": 0 if state["gps"] == "denied" else 100}, "mode": "self-healing sensor fusion"}

@app.get("/api/detections")
def detections():
    tick(); obstacle = state["obstacle_injected"]
    return {"detections": [
        {"type":"obstacle","label":"Building","distance_m":18.4,"risk":"low","confidence":96},
        {"type":"dynamic_obstacle","label":"Vehicle","distance_m":27.1,"risk":"high" if obstacle else "low","confidence":91 if obstacle else 82},
        {"type":"landing_zone","label":"Landing Pad","distance_m":42.0,"risk":"low","confidence":94},
        {"type":"gps_loss","label":"GPS Denied","distance_m":0,"risk":"warning","confidence":100},
        {"type":"collision_risk","label":"Trajectory Risk","distance_m":11.6 if obstacle else 31.0,"risk":"high" if obstacle else "low","confidence":93},
    ]}

@app.get("/api/path")
def path():
    detour = state["obstacle_injected"]
    points = [{"x":0,"y":0,"z":5},{"x":8,"y":2,"z":8},{"x":16,"y":5,"z":12}]
    if detour: points += [{"x":20,"y":11,"z":14},{"x":25,"y":9,"z":15}]
    points += [{"x":30,"y":0,"z":15}]
    return {"path_version":state["path_version"],"planner":"Risk-aware 3D A*","risk_score":31 if detour else 18,"distance_m":44.6 if detour else 39.8,"estimated_time_s":16.7 if detour else 14.2,"battery_cost_percent":5.6 if detour else 4.8,"position_uncertainty_m":state["position_error"],"points":points,"corridor_radius_m":4.5 if detour else 3.0}

@app.get("/api/analytics")
def analytics():
    return {"mission_success":98,"max_position_error_m":0.18,"path_deviation_percent":1.7,"landing_error_cm":4.2,"battery_used_percent":round(78-state["battery"],1),"sensor_fusion_confidence":round(state["confidence"],1)}
