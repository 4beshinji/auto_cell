"""MQTT virtual bioreactor backed by sim.plant_model.PlantModel."""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from typing import Any

from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from auto_cell.gateway.correlation import now_iso
from auto_cell.gateway.idempotency import IdempotencyStore
from auto_cell.gateway.mqtt_client import MqttClient
from sim.plant_model import Actuators, PlantModel

logger = logging.getLogger(__name__)


class DummyBioreactorEdge(MqttClient):
    """Virtual edge that drives plant_model over MQTT."""

    def __init__(
        self,
        culture_unit_id: str,
        *,
        device_id: str = "bioreactor_01",
        broker: str = "localhost",
        port: int = 1883,
        cycle_interval_s: float = 30.0,
    ) -> None:
        client_id = f"ve_{culture_unit_id}_{device_id}"
        super().__init__(client_id, broker, port)
        self.cu = culture_unit_id
        self.device_id = device_id
        self.cycle_interval_s = cycle_interval_s

        self.actuators = Actuators(
            perfusion_rate_vvd=0.0,
            agitation_rpm=80.0,
            do_setpoint=40.0,
            ph_setpoint=7.1,
            feed_glucose=0.0,
            feed_glutamine=0.0,
        )
        self.latest_sensors: dict[str, Any] = {}
        self.idempotency = IdempotencyStore(ttl_seconds=86400)
        self._plant = PlantModel()

    async def start(self) -> None:
        self.connect()
        await self.subscribe(f"cell/{self.cu}/cmd/{self.device_id}/+", self._on_cmd, qos=1)
        await self.subscribe(
            f"cell/{self.cu}/program/{self.device_id}/request",
            self._on_program_request,
            qos=1,
        )
        self.publish(
            f"cell/{self.cu}/state/device/{self.device_id}",
            {"status": "ONLINE", "device_id": self.device_id, "ts": now_iso()},
            retain=True,
        )

    # ------------------------------------------------------------------
    # command handling
    # ------------------------------------------------------------------
    def _on_cmd(self, topic: str, payload: dict[str, Any], properties: Properties | None) -> None:
        function_id = topic.split("/")[-1]
        request_id = payload.get("request_id", "unknown")
        correlation_id = payload.get("correlation_id", request_id)

        if self.idempotency.is_known(request_id):
            cached = self.idempotency.get(request_id)
            self._ack(function_id, "replayed", cached.result if cached else None, correlation_id, request_id)
            return

        status, result = self._execute(function_id, payload.get("args", {}))
        self.idempotency.save(request_id, status, result)
        self._ack(function_id, status, result, correlation_id, request_id)

    def _execute(self, function_id: str, args: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        try:
            if function_id == "set_perfusion_rate":
                self.actuators = self._replace(perfusion_rate_vvd=float(args["vvd"]))
            elif function_id == "set_agitation_rpm":
                self.actuators = self._replace(agitation_rpm=float(args["rpm"]))
            elif function_id == "set_gas_setpoint":
                gas = args.get("gas")
                if gas == "do":
                    self.actuators = self._replace(do_setpoint=float(args["setpoint"]))
                elif gas == "ph":
                    self.actuators = self._replace(ph_setpoint=float(args["setpoint"]))
            elif function_id == "feed":
                glucose = float(args.get("glucose_mM", 0.0))
                glutamine = float(args.get("glutamine_mM", 0.0))
                volume_ml = float(args.get("volume_ml", 0.0))
                # Approximate mmol from mM * L
                self.actuators = self._replace(
                    feed_glucose=self.actuators.feed_glucose + glucose * volume_ml / 1000.0,
                    feed_glutamine=self.actuators.feed_glutamine + glutamine * volume_ml / 1000.0,
                )
            elif function_id == "exchange_media":
                # plant_model perfusion handles media exchange implicitly.
                pass
            elif function_id == "trigger_passage":
                self.actuators = self._replace(perfusion_rate_vvd=0.0)
                self._plant.reset_after_passage()
            elif function_id == "take_sample":
                return "completed", {"sensors": self.latest_sensors.copy()}
            else:
                return "failed", {"error": f"unknown function: {function_id}"}
            return "accepted", {"actuators": self.actuators.__dict__}
        except Exception as exc:
            return "failed", {"error": str(exc)}

    def _replace(self, **kwargs: Any) -> Actuators:
        return Actuators(**{**self.actuators.__dict__, **kwargs})

    def _ack(
        self,
        function_id: str,
        status: str,
        result: dict[str, Any] | None,
        correlation_id: str,
        request_id: str,
    ) -> None:
        topic = f"cell/{self.cu}/ack/{self.device_id}/{function_id}"
        ack = {
            "status": status,
            "result": result,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "timestamp": now_iso(),
            "source": self.device_id,
        }
        props = Properties(PacketTypes.PUBLISH)
        props.CorrelationData = correlation_id.encode("utf-8")
        self.publish(topic, ack, qos=1, properties=props)

    # ------------------------------------------------------------------
    # program handling
    # ------------------------------------------------------------------
    def _on_program_request(self, topic: str, payload: dict[str, Any], properties: Properties | None) -> None:
        request_id = payload.get("request_id", "unknown")
        correlation_id = payload.get("correlation_id", request_id)
        result = {"status": "program_stub_executed", "program_id": payload.get("program_id")}
        self.publish(
            f"cell/{self.cu}/program/{self.device_id}/response",
            {
                "status": "completed",
                "result": result,
                "correlation_id": correlation_id,
                "request_id": request_id,
                "timestamp": now_iso(),
                "source": self.device_id,
            },
            qos=1,
        )

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        asyncio.run(self.start())
        try:
            while True:
                self.tick()
                time.sleep(self.cycle_interval_s)
        finally:
            self.disconnect()

    def tick(self) -> dict[str, Any]:
        """Run one plant step and publish telemetry if connected."""
        sensors = self._plant.step(self.actuators, dt=self.cycle_interval_s)
        self.latest_sensors = sensors.__dict__

        telemetry = {
            "timestamp": now_iso(),
            "device_id": self.device_id,
            "actuators": self.actuators.__dict__,
            "values": self.latest_sensors,
        }
        if self.is_connected():
            self.publish(
                f"cell/{self.cu}/telemetry/{self.device_id}/all",
                telemetry,
                qos=1,
                retain=True,
            )

            for key, value in self.latest_sensors.items():
                self.publish(
                    f"cell/{self.cu}/telemetry/{self.device_id}/{key}",
                    {
                        "timestamp": now_iso(),
                        "value": value,
                        "unit": self._guess_unit(key),
                        "quality": "GOOD",
                        "source": self.device_id,
                    },
                    qos=1,
                    retain=True,
                )
        return telemetry

    @staticmethod
    def _guess_unit(key: str) -> str:
        unit_map = {
            "vcd": "cells/mL",
            "viability": "ratio",
            "glucose": "mM",
            "lactate": "mM",
            "glutamine": "mM",
            "osmolality": "mOsm/kg",
            "aggregate_diameter_um": "um",
            "do_percent": "percent",
            "ph": "pH",
            "temp_c": "C",
        }
        return unit_map.get(key, "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cu", default="cu_001")
    parser.add_argument("--device", default="bioreactor_01")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--interval", type=float, default=30.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    edge = DummyBioreactorEdge(
        culture_unit_id=args.cu,
        device_id=args.device,
        broker=args.broker,
        port=args.port,
        cycle_interval_s=args.interval,
    )
    edge.run()


if __name__ == "__main__":
    main()
