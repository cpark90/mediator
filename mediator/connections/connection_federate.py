import logging
import time

import carla  # pylint: disable=import-error
from .constants import INVALID_ACTOR_ID, SPAWN_OFFSET_Z

from mediator.connections import ConnectionBase, TimestampMessage
from federate_message_wrapper_pb2 import FederateMessageWrapper
from mediator_status_pb2 import MediatorStatus
from types_pb2 import StatusType


class ConnectionCarla(ConnectionBase):
    def __init__(self, step_length, delay, apply_to_function, send_to_function, region_contraint, host='127.0.0.1', port='8913'):
        super().__init__(apply_to_function, send_to_function, region_contraint)
        self.connect(host, port)

        self.blueprint_library = self.world.get_blueprint_library()
        self.step_length = step_length

        # The following sets contain updated information for the current frame.
        self._active_actors = set()
        self.spawned_actors = set()
        self.destroyed_actors = set()

        # Set traffic lights.
        self._tls = {}  # {landmark_id: traffic_ligth_actor}

        tmp_map = self.world.get_map()
        for landmark in tmp_map.get_all_landmarks_of_type('1000001'):
            if landmark.id != '':
                traffic_ligth = self.world.get_traffic_light(landmark)
                if traffic_ligth is not None:
                    self._tls[landmark.id] = traffic_ligth
                else:
                    logging.warning('Landmark %s is not linked to any traffic light', landmark.id)

        self.init_sending_thread(delay=delay)

    def connect(self, host, port):
        maxConnectionAttempts = 5
        while maxConnectionAttempts > 0:
            connected = True
            maxConnectionAttempts = maxConnectionAttempts - 1
            try:
                self.client = carla.Client(host, port)
                self.client.set_timeout(5.0)
                self.world = self.client.get_world()
            except:
                logging.info("reconnect carla")
                connected=False
            if connected:
                logging.info('Connection to carla server. Host: %s Port: %s', host, port)
                logging.info("CARLA simulator connected")
                break
            if maxConnectionAttempts == 0 and connected == False:
                logging.info("Maximum connection attempts reached and connecting to CARLA simulator failed.")
                raise RuntimeError("Can not connect CARLA server. Check whether CARLA server starts or not.")

    def process_messages_until_timestamp(self, timestamp):
        received_messages = self.received_message_buffer.get_past_messages_by_timestamp(timestamp=timestamp)
        for message in received_messages:
            self.process_received_message(message.data)

    def process_received_message(self, wrapper):
        if wrapper.WhichOneof("message") is "mediatorStatus":
            logging.info("mediatorStatus")
        elif wrapper.WhichOneof("message") is "simulationStep":
            logging.info("simulationStep")
            wrapper.simulationStep

    def process_sending_message(self):
        while self.sending_message_buffer:
            message = self.sending_message_buffer.popleft()
            wrapper = FederateMessageWrapper()
            if message.__class__.__name__ is "MediatorStatus":
                wrapper.mediatorStatus.CopyFrom(message)
            elif message.__class__.__name__ is "SimulationStep":
                wrapper.simulationStep.CopyFrom(message)

            self.mosaic_socket.sendall(struct.pack('>I', wrapper.ByteSize()))
            self.mosaic_socket.sendall(wrapper.SerializeToString())

    def validate_out_of_region(self, region, message):
        return False
    
    def validate_before_timestamp(self, timestamp, message):
        return False
    
    def receive_message(self):
        # Update data structures for the current frame.
        current_actors = set(
            [vehicle.id for vehicle in self.world.get_actors().filter('vehicle.*')])
        self.spawned_actors = current_actors.difference(self._active_actors)
        self.destroyed_actors = self._active_actors.difference(current_actors)
        self._active_actors = current_actors

        wrapper = FederateMessageWrapper()
        return wrapper
    
    def receiving_thread_function(self):
        while not self.stop_event.is_set():
            wrapper = self.receive_message()
            if wrapper is None:
                break
            time.sleep(self.delay)
            if self.validate_out_of_region(region=self.region_constraint, message=wrapper):
                continue
            if self.validate_before_timestamp(timestamp=self.applicable_timebound["lower"], message=wrapper):
                continue
            message = TimestampMessage(timestamp=0, data=wrapper)
            self.received_message_buffer.add_message(message=message)

            if message.timestamp < self.applicable_timebound["upper"]:
                self.process_messages_until_timestamp(timestamp=self.applicable_timebound["upper"])
    
    def sending_thread_function(self):
        while not self.stop_event.is_set():
            self.process_sending_message()
            time.sleep(self.delay)

    # CARLA method
    def tick(self):
        """
        Tick to carla simulation.
        """
        self.world.tick()

    def stop(self):
        """
        Closes carla client.
        """
        for actor in self.world.get_actors():
            if actor.type_id == 'traffic.traffic_light':
                actor.freeze(False)

        super().stop()

    def get_actor(self, actor_id):
        """
        Accessor for carla actor.
        """
        return self.world.get_actor(actor_id)

    # This is a workaround to fix synchronization issues when other carla clients remove an actor in
    # carla without waiting for tick (e.g., running sumo co-simulation and manual control at the
    # same time)
    def get_actor_light_state(self, actor_id):
        """
        Accessor for carla actor light state.

        If the actor is not alive, returns None.
        """
        try:
            actor = self.get_actor(actor_id)
            return actor.get_light_state()
        except RuntimeError:
            return None

    @property
    def traffic_light_ids(self):
        return set(self._tls.keys())

    def get_traffic_light_state(self, landmark_id):
        """
        Accessor for traffic light state.

        If the traffic ligth does not exist, returns None.
        """
        if landmark_id not in self._tls:
            return None
        return self._tls[landmark_id].state

    def switch_off_traffic_lights(self):
        """
        Switch off all traffic lights.
        """
        for actor in self.world.get_actors():
            if actor.type_id == 'traffic.traffic_light':
                actor.freeze(True)
                # We set the traffic light to 'green' because 'off' state sets the traffic light to
                # 'red'.
                actor.set_state(carla.TrafficLightState.Green)

    def spawn_actor(self, blueprint, transform):
        """
        Spawns a new actor.

            :param blueprint: blueprint of the actor to be spawned.
            :param transform: transform where the actor will be spawned.
            :return: actor id if the actor is successfully spawned. Otherwise, INVALID_ACTOR_ID.
        """
        transform = carla.Transform(transform.location + carla.Location(0, 0, SPAWN_OFFSET_Z),
                                    transform.rotation)

        batch = [
            carla.command.SpawnActor(blueprint, transform).then(
                carla.command.SetSimulatePhysics(carla.command.FutureActor, False))
        ]
        response = self.client.apply_batch_sync(batch, False)[0]
        if response.error:
            logging.error('Spawn carla actor failed. %s', response.error)
            return INVALID_ACTOR_ID

        return response.actor_id

    def destroy_actor(self, actor_id):
        """
        Destroys the given actor.
        """
        actor = self.world.get_actor(actor_id)
        if actor is not None:
            return actor.destroy()
        return False

    def synchronize_vehicle(self, vehicle_id, transform, lights=None):
        """
        Updates vehicle state.

            :param vehicle_id: id of the actor to be updated.
            :param transform: new vehicle transform (i.e., position and rotation).
            :param lights: new vehicle light state.
            :return: True if successfully updated. Otherwise, False.
        """
        vehicle = self.world.get_actor(vehicle_id)
        if vehicle is None:
            return False

        vehicle.set_transform(transform)
        if lights is not None:
            vehicle.set_light_state(carla.VehicleLightState(lights))
        return True

    def synchronize_traffic_light(self, landmark_id, state):
        """
        Updates traffic light state.

            :param landmark_id: id of the landmark to be updated.
            :param state: new traffic light state.
            :return: True if successfully updated. Otherwise, False.
        """
        if not landmark_id in self._tls:
            logging.warning('Landmark %s not found in carla', landmark_id)
            return False

        traffic_light = self._tls[landmark_id]
        traffic_light.set_state(state)
        return True