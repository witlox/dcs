import base64
import json
import logging
from logging.config import dictConfig
import uuid
import boto.ec2
from settings import Settings

# currently only 1 machine per reservation

with open('logging.json') as jl:
    dictConfig(json.load(jl))

settings = Settings()


def start_machine(ami, instance):
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None, None

    worker_id = 'jm-%s' % uuid.uuid4()
    logging.info('Request workerID = %s' % worker_id)
    try:
        reservation = ec2.run_instances(
            ami,
            security_groups=[settings.aws_seqgrp],
            instance_type=instance,
            user_data=base64.b64encode(worker_id),
            instance_initiated_shutdown_behavior='terminate',
        )
        logging.info('Reservation %s for worker %s' % (reservation.id, worker_id))
        return worker_id, reservation.id
    except Exception, e:
        logging.exception('Cannot reserve instance %s for type %s (%s)' % (ami, instance, e))
        return None, None
    finally:
        if ec2:
            ec2.close()


def terminate_machine(instance_id):
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None
    try:
        terminated = ec2.terminate_instances([instance_id])
        logging.info('Succesfully terminated %d instances' % (len(terminated)))
        return terminated
    except Exception, e:
        logging.exception('Cannot terminate instance %s (%s)' % (instance_id, e))
        return None
    finally:
        if ec2:
            ec2.close()


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
    except Exception, e:
        logging.exception('Could not get reservations for %s (%s)' % (reservation_id, e))
        return None, None
    finally:
        if ec2:
            ec2.close()


def get_status(instance_id):
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None
    try:
        statuses = ec2.get_all_instance_status(instance_ids=[instance_id])
        if len(statuses) == 1:
            logging.info('current %s status: %s' % (instance_id, statuses[0].system_status))
            return statuses[0].system_status
        return None
    except Exception, e:
        logging.exception('Could not get status for %s (%s)' % (instance_id, e))
        return None
    finally:
        if ec2:
            ec2.close()


def get_max_instances():
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None
    try:
        attributes = ec2.describe_account_attributes()
        for attribute in attributes:
            if attribute.attribute_name and 'max-instances' in attribute.attribute_name.lower():
                return int(attribute.attribute_values[0])
        return 0
    except Exception, e:
        logging.exception('Could not get attributes (%s)' % e)
        return None
    finally:
        if ec2:
            ec2.close()


def active_instance_count():
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None
    try:
        total = 0
        reservations = ec2.get_all_reservations()
        for reservation in reservations:
            total += len(reservation.instances)
        return total
    except Exception, e:
        logging.exception('Could not get attributes (%s)' % e)
        return None
    finally:
        if ec2:
            ec2.close()


def get_storage_usage(instances):
    ec2 = boto.ec2.connect_to_region(settings.aws_region,
                                     aws_access_key_id=settings.aws_access,
                                     aws_secret_access_key=settings.aws_secret)

    if not ec2:
        logging.error('Cannot connect to region %s' % settings.aws_region)
        return None
    try:
        total = 0
        volumes = ec2.get_all_volumes()
        for volume in volumes:
            if volume.attach_data.instance_id in instances:
                total += volume.size
        return total
    except Exception, e:
        logging.exception('Could not get attributes (%s)' % e)
        return None
    finally:
        if ec2:
            ec2.close()
