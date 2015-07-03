import base64
import json
import logging
from logging.config import dictConfig
import uuid
import boto
from settings import Settings

# currently only 1 machine per reservation

dictConfig(json.load('logging.json'))

settings = Settings()

def start_machine(ami, instance):
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None

    worker_id = 'jm-%s' % uuid.uuid4()
    logging.info('Request workerID = %s', worker_id)
    try:
        reservation = ec2.run_instances(
            ami,
            security_groups=[settings.aws_seqgrp],
            instance_type=instance,
            user_data=base64.b64encode(worker_id),
            instance_initiated_shutdown_behavior='terminate',
        )
        logging.info('Reservation %s for worker %s', reservation.id, worker_id)
        return worker_id, reservation.id
    except Exception:
        logging.exception('Cannot reserve instance')
        return None

def terminate_machine(instance_id):
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None
    try:
        terminated = ec2.terminate_instances([instance_id])
        logging.info('Succesfully terminated %d instances %s', len(terminated), ' '.join(terminated))
        return terminated
    except Exception:
        logging.exception('Cannot terminate instance %s' % instance_id)
        return None

def my_booted_machine(reservation_id):
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None, None
    try:
        reservations = ec2.get_all_reservations()
        reservation = [r for r in reservations if r.id == reservation_id]
        if len(reservation) > 0 and len(reservation[0].instances) > 0:
            return reservation[0].instances[0].id, reservation[0].instances[0].ip_address
    except Exception:
        logging.exception('Could not get reservations')
    return None, None
