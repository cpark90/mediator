#!/usr/bin/env python

# Copyright (c) 2020 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

# ==================================================================================================
# -- imports ---------------------------------------------------------------------------------------
# ==================================================================================================

import argparse
import logging
import shutil
import tempfile


# ==================================================================================================
# -- find carla module -----------------------------------------------------------------------------
# ==================================================================================================

import glob
import os
import sys

try:
    sys.path.append(
        glob.glob('/tmp/mediator_carla/carla/carla-federate/simulations/carla-*%d.%d-%s.egg' %
                  (sys.version_info.major, sys.version_info.minor,
                   'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    print("Can not find carla library .egg")

# ==================================================================================================
# -- find traci module -----------------------------------------------------------------------------
# ==================================================================================================

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

# ==================================================================================================
# -- imports ---------------------------------------------------------------------------------------
# ==================================================================================================

import sumolib  # pylint: disable=wrong-import-position
import traci  # pylint: disable=wrong-import-position

from carla_integration.carla_simulation import CarlaSimulation  # pylint: disable=wrong-import-position
from carla_integration.sumo_simulation import SumoSimulation  # pylint: disable=wrong-import-position

from backup.carla_integration.mediator import Mediator  # pylint: disable=wrong-import-position

from util.netconvert_carla import netconvert_carla
# ==================================================================================================
# -- main ------------------------------------------------------------------------------------------
# ==================================================================================================

class MediatorBase(object):
    # initialize connection to redis server, federate, mosaic / set interesting region, time advance mode / 
    def __init__(self, args):
        raise NotImplementedError
    
    def establish_connection_to_mosaic(self):
        raise NotImplementedError
    
    def establish_connection_to_federate(self):
        raise NotImplementedError
    
    def establish_connection_to_other_federate(self):
        raise NotImplementedError
    
    def establish_connection_to_traffic_cache(self):
        raise NotImplementedError
    
    # passive when stand-by phase: receive traffic update from mosaic and other federate -> local region filtering ->
    # retrieve traffic agent from redis -> apply traffic agent to federate
    def apply_to_federate(self):
        raise NotImplementedError
    
    # passive get traffic agent from federate -> local region filtering -> apply traffic agent to traffic cache
    def apply_to_traffic_cache(self):
        raise NotImplementedError

    # wait then lock apply_to_federate -> federate time advance -> apply_to_traffic_cache -> send to other federate and mosaic
    def tick(self):
        raise NotImplementedError
    
    def immediate_tick(self):
        raise NotImplementedError

    def cyclic_tick(self):
        raise NotImplementedError        

def main(args):
    # ----------------
    # carla simulation
    # ----------------
    carla_simulation = CarlaSimulation(args.host, args.port, args.step_length)
    if args.map is not None:
        print('load map %r.' % args.map)
        world = carla_simulation.client.load_world(args.map)
    else:
        world = carla_simulation.client.get_world()

    carla_simulation = CarlaSimulation(args.host, args.port, args.step_length)
    logging.info("Carla initialize")
    # ---------------
    # sumo simulation
    # ---------------
    if args.net_file is not None:
        sumo_net=sumolib.net.readNet(args.net_file)
        logging.info("load net file")
    else:
        # Temporal folder to save intermediate files.
        tmpdir = tempfile.mkdtemp()
        current_map = world.get_map()
        xodr_file = os.path.join(tmpdir, current_map.name + '.xodr')
        current_map.save_to_disk(xodr_file)
        net_file = os.path.join(tmpdir, current_map.name + '.net.xml')
        netconvert_carla(xodr_file, net_file, guess_tls=True)
        sumo_net = sumolib.net.readNet(net_file)

    sumo_simulation = SumoSimulation(sumo_net,
                                     args.step_length,
                                     host=args.bridge_server_host,
                                     port=args.bridge_server_port)

    logging.info("Sumo initialize")
    # ---------------
    # synchronization
    # ---------------
    synchronization = Mediator(sumo_simulation, carla_simulation, args.tls_manager,
                                                args.sync_vehicle_color, args.sync_vehicle_lights)

    logging.info("Simulation synchronization initialize")
    # start simulation synchronization
    try:
        while True:
            synchronization.tick()

    except KeyboardInterrupt:
        logging.info('Cancelled by user.')
    except traci.exceptions.FatalTraCIError:
        logging.info("Socket server closed")

    finally:
        try:
            synchronization.close()
        except:
            logging.info("Connection closed")
        if "tmpdir" in locals():
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)



if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument('--host',
                           metavar='H',
                           default='127.0.0.1',
                           help='IP of the CARLA host server (default: 127.0.0.1)')
    argparser.add_argument('-p',
                           '--port',
                           metavar='P',
                           default=2000,
                           type=int,
                           help='CARLA TCP port to listen to (default: 2000)')
    argparser.add_argument('--bridge-server-host',
                           default='localhost',
                           help='IP of the bridge host server (default: None)')
    argparser.add_argument('--bridge-server-port',
                           default=8913,
                           type=int,
                           help='TCP port to listen to (default: None)')
    argparser.add_argument('-m',
                           '--map',
                            help='load a new map')
    argparser.add_argument('net_file',
                           type=str,
                           default=None,
                           help='load the net file')
    argparser.add_argument('--step-length',
                           default=0.05,
                           type=float,
                           help='set fixed delta seconds (default: 0.05s)')
    argparser.add_argument('--sync-vehicle-lights',
                           action='store_true',
                           help='synchronize vehicle lights state (default: False)')
    argparser.add_argument('--sync-vehicle-color',
                           action='store_true',
                           help='synchronize vehicle color (default: False)')
    argparser.add_argument('--sync-vehicle-all',
                           action='store_true',
                           help='synchronize all vehicle properties (default: False)')
    argparser.add_argument('--tls-manager',
                           type=str,
                           choices=['none', 'sumo', 'carla'],
                           help="select traffic light manager (default: none)",
                           default='none')
    argparser.add_argument('--debug', action='store_true', help='enable debug messages')
    args = argparser.parse_args()

    if args.sync_vehicle_all is True:
        args.sync_vehicle_lights = True
        args.sync_vehicle_color = True

    if args.debug:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    main(args)
