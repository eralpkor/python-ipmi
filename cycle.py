#!/usr/bin/python
# @Eralp
import logging
import requests
import time
from datetime import datetime
import subprocess
import os
# import config
import urllib3
import colorlog
import sys
import math
import ping_ip
# from pythonping import ping
import argparse
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# sudo setcap cap_net_raw+ep $(readlink -f $(which python))

parser = argparse.ArgumentParser(description="Power cycle script", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
# parser.add_argument("-h", "--help", help="show this help message")
parser.add_argument("-u", "--username", help="BMC user name", type=str, required=True)
parser.add_argument("-p", "--password", help="BMC password", type=str, required=True)
parser.add_argument("-i", "--ipaddress", help="BMC ip address", type=str, required=True)
parser.add_argument("-c", "--cipher", help="BMC security cipher", type=str, required=True)
parser.add_argument("-t", "--timer", help="Test running time in hours", type=int, required=True)
parser.add_argument("-l", "--log", help="Log file name", type=str, required=True)
parser.add_argument("-m", "--target", help="How many cycles", default=1000 ,type=int)
parser.add_argument("-w", "--clearlogs", help="Clear all system logs", default=False, required=True)
parser.add_argument("-a", "--accycle", help="If system going to be AC cycled", default=False, required=False)
# parser.add_argument("v", "--ipv6", help="IPv6 if any", type=str, required=False)
config = parser.parse_args()
print(f"ip address {config.ipaddress}")
# Setup logger
logger = logging.getLogger(__name__)
stdout = colorlog.StreamHandler(stream=sys.stdout)
fmt = colorlog.ColoredFormatter(
    "%(name)s: %(white)s%(asctime)s%(reset)s | %(log_color)s%(levelname)s%(reset)s | %(blue)s%(filename)s:%(lineno)s%(reset)s | %(process)d >>> %(log_color)s%(message)s%(reset)s"
)
stdout.setFormatter(fmt)
logger.addHandler(stdout)
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG) # Logger for debug script

# variables
bmc_ip = config.ipaddress
user = config.username
password = config.password
target_cycle = config.target
cipher = config.cipher
log = config.log
# ipv6_cycle = False
# if config.ipv6:
#     ipv6_cycle = True
# print(ipv6_cycle)
# ac = config.accycle.lower()
# if ac == "no":
#     ac = False
# if ac == "yes":
#     ac = True
# Get ipmi commands
# ipmiCommand = config.ipmiCommand
# Cycle raw commands
ipmiCommand = [
    ["0x00", "0x02", "0x00", "off"],
    ["0x00", "0x02", "0x01", "on"],
    ["0x00", "0x02", "0x02", "cycle"],
    ["0x00", "0x02", "0x03", "reset"]]
command_length = len(ipmiCommand)
folder_path = ''
filename = ''
time_tag = datetime.now().strftime("%Y%m%d_%H%M%S.%f")
log_file = ''
test_log_path = 'logs/'
test_target_run = config.timer * 3600000
logger.info(f"Test will run {math.trunc(test_target_run / 60000)} minutes")
test_start_time = datetime.now()

# Create log file
folder_path = test_log_path + time_tag + '_' + bmc_ip
try:
    os.makedirs(folder_path)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
log_file = folder_path + '/' + log + "_" + bmc_ip + '.log'

logging.basicConfig(
    filename=log_file, format="%(levelname)s | %(asctime)s | %(message)s", level=logging.DEBUG)

# Start power cycle with these settings
logger.info('XCC IP: ' + bmc_ip)
logger.info('XCC ID: ' + user)
logger.info('XCC PW: ' + password)

# HTTP Request variables
session = requests.Session()
session.auth = (user, password)
rest_api = 'https://' + bmc_ip + '/redfish/v1/Systems/1'
post_data = {}

# ping_ip.ping_ip(ip_address, duration)
if not ping_ip.ping_ip(bmc_ip, 2):
    logger.error(f"Cannot ping BMC ip {bmc_ip}")
    sys.exit(1)

if ping_ip.ping_ip(bmc_ip, 2):
    logger.info(f"Verifying XCC IP {bmc_ip} is pingable...")
    time.sleep(3)
    logger.info(f"XCC ping successful, moving on.")

# HTTP RedFish call to check system status
def system_status():
    try:
        r = session.get(rest_api, verify=False)
        r.raise_for_status()
        status = r.json()["Oem"]["Lenovo"]["SystemStatus"]
        return status
    except requests.exceptions.HTTPError as errh:
        logger.error("HTTP Error, check username/password")
        logger.error(errh.args[0])
        raise sys.exit(errh)
    except requests.exceptions.ReadTimeout as errrt:
        logger.error("Time out")
        raise sys.exit(errrt)
    except requests.exceptions.ConnectionError as conerr:
        logger.error("Connection error")
        raise sys.exit(conerr)
        # if r.status_code == "401":
        #     logger.error(f"User or password is incorrect. You entered: {user}, {password}")
        #     sys.exit(1)
        # else:
        
    except requests.exceptions.RequestException as e:
        logger.error("Cannot connect to BMC, exiting.")
        raise sys.exit(e)

# Check system status before cycle test
status = system_status()
logger.info(f"System status {status} on {rest_api}")

# Windows only
# ipmi_path = 'C:\\python-ipmi\\ipmi\\'
# ipmi_cmd = 'ipmitool.exe'
r = ''
# ipmitool
def ipmi_cycle(ip_address, r, a, b, c):
    try:
        p = subprocess.run(
            f"ipmitool -I lanplus -C {cipher} -H {ip_address} -U {user} -P {password} {r} {a} {b} {c}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if p.returncode == 0:
            logger.info(f"System power status: {p.stdout}")
            time.sleep(10)
            logger.info(f"ipmi raw command sent {a}, {b}, {c}")
        # print(f"check return code {p.check_returncode()}")

        if p.returncode != 0:
            logger.critical(f"Exiting script, check your ipmi settings/status {p.stderr}")
            sys.exit(1)

    except Exception as e:
        logger.critical(f"Error: {e}")
        sys.exit(e)

# Check if IPMI over LAN is active
ipmi_cycle(bmc_ip, "", "power", "status", "")
# Critical Interrupt

# Clear logs before running the script
def clear_system_logs(rest_api, session):
    try:
        # Clear Audit logs
        a = session.post(rest_api +
                        '/LogServices/AuditLog/Actions/LogService.ClearLog', json=post_data, verify=False)
        logger.info("Audit logs cleared.")
        a.raise_for_status()
        # status = a.json()["Oem"]["Lenovo"]["SystemStatus"]
        # return status
    except requests.exceptions.HTTPError as errh:
        logger.error("HTTP Error, check username/password")
        logger.error(errh.args[0])
        raise sys.exit(errh)
    except requests.exceptions.ReadTimeout as errrt:
        logger.error("Time out")
        raise sys.exit(errrt)
    except requests.exceptions.ConnectionError as conerr:
        logger.error("Connection error")
        raise sys.exit(conerr)
    except requests.exceptions.RequestException as e:
        logger.error("Cannot connect to BMC, exiting.")
        raise sys.exit(e)
    
    try:
        # Clear SEL logs
        s = session.post(rest_api + '/LogServices/SEL/Actions/LogService.ClearLog',
                        json=post_data, verify=False)
        logger.info(f"SEL logs cleared on {rest_api}")
    except requests.exceptions.HTTPError as errh:
        logger.error("HTTP Error, check username/password")
        logger.error(errh.args[0])
        raise sys.exit(errh)
    except requests.exceptions.ReadTimeout as errrt:
        logger.error("Time out")
        raise sys.exit(errrt)
    except requests.exceptions.ConnectionError as conerr:
        logger.error("Connection error")
        raise sys.exit(conerr)
    except requests.exceptions.RequestException as e:
        logger.error("Cannot connect to BMC, exiting.")
        raise sys.exit(e)
    
    try:
        # Clear Event logs
        e = session.post(rest_api + '/LogServices/PlatformLog/Actions/LogService.ClearLog',
                        json=post_data, verify=False)
        logger.info("Event logs cleared.")
    except requests.exceptions.HTTPError as errh:
        logger.error("HTTP Error, check username/password")
        logger.error(errh.args[0])
        raise sys.exit(errh)
    except requests.exceptions.ReadTimeout as errrt:
        logger.error("Time out")
        raise sys.exit(errrt)
    except requests.exceptions.ConnectionError as conerr:
        logger.error("Connection error")
        raise sys.exit(conerr)
    except requests.exceptions.RequestException as e:
        logger.error("Cannot connect to BMC, exiting.")
        raise sys.exit(e)

def main():
    is_system_busy = False
    index = 0
    os_booted = False
    keep_calling = True
    command = []
    cycle_count = 1
    ac_cycled = False
    logger.info(f"*************\n Cycle test start {datetime.now()} \n***********")
    # Clear all sytem logs
    print(f"Clear logs {config.clearlogs}")
    if config.clearlogs == True:
        clear_system_logs(rest_api, session)

    print("Sleeping 5 seconds.")
    time.sleep(5)

    while keep_calling:
        is_powered_off = False
        status = system_status()
        logger.info(f"*****************\n********** Power Cycle {cycle_count} start. ***********\n*****************")
        if status == "SystemPowerOff_StateUnknown":
            is_powered_off = True
        logger.info(f"is powered off {is_powered_off}")
        cycle_time_start = datetime.now()
        for raw in ipmiCommand:
            logger.info(f"is system busy {is_system_busy}")
            command = raw  # type: ignore
            status = system_status()
            logger.info(f"Redfish system status {status}")
            # AC cycle stuff

            if status == "SystemOn_StartingUEFI" or \
                    status == "SystemRunningInUEFI" or \
                    status == "BootingOSOrInUndetectedOS":
                is_system_busy = True
                logger.info(f"System busy {is_system_busy}")

            wait_count = 1

            # Wait until next ipmi command
            while is_system_busy:
                logger.warning(f"Wait count {wait_count}")
                if wait_count > 90:
                    logger.critical(
                        f"Waited 30 minutes System state did not change, exiting test.\
                             Redfish system status: {system_status()}")
                    sys.exit(1)

                logger.info("Sleeping 20 seconds to detect power state.")
                time.sleep(20)
                status = system_status()
                logger.info(f"Redfish system status {status}")
                # Check redFish state, if not OS booted or powered off keep checking
                if status == "OSBooted" or \
                        status == "SystemPowerOff_StateUnknown":
                    is_system_busy = False
                    logger.info(f"Is system busy booting {is_system_busy}")
                wait_count += 1

            logger.info(f"Sleep 60 Seconds before raw command {command}")
            time.sleep(60)

            ipmi_cycle(bmc_ip, "raw", command[0], command[1], command[2])
            logger.info(f"ipmi power {ipmiCommand[index][3]} command sent.")
            is_system_busy = True
            logger.info(f"is system busy {is_system_busy}")

            # Check if ipmi off command turned off the system
            if command[2] == "0x00":
                wait_count = 1
                logger.info(f"Shut down wait count {wait_count}")
                while not is_powered_off:
                    status = system_status()
                    if wait_count > 90:
                        logger.critical(
                            f"Waited 30 minutes but System did not power off, test exited. Power status {status}")
                        sys.exit(1)

                    logger.info(
                        "Sleep 20 seconds to check if system powered off.")
                    time.sleep(20)
                    status = system_status()
                    logger.info(f"Redfish system status {status}")

                    if status == "SystemPowerOff_StateUnknown":
                        is_powered_off = True
                        logger.info(f"System powered off {is_powered_off}")
                    else:
                        logger.warning(
                            f"System did not powered off. {is_powered_off}")
                    wait_count += 1

            # Numerator for cycle command loop
            index += 1

            if command[2] == "0x01":
                wait_count = 1
                logger.info(f"Power on wait count {wait_count}")
                while not os_booted:
                    status = system_status()
                    if wait_count > 90:
                        logger.critical(
                            f"Waited 30 minutes, but system did not power on. System status: {status}")
                        sys.exit(1)

                    logger.info(
                        "Sleep 20 seconds to check if system powered on.")
                    time.sleep(20)
                    status = system_status()
                    logger.info(f"Redfish system status {status}")
                    logger.info(f"Wait count {wait_count}")
                    if status == "OSBooted":
                        os_booted = True
                        logger.info(f"OS booted {os_booted}")
                        logger.info(f"Sleeping 30 seconds to do next ipmi command")
                        time.sleep(30)
                    else:
                        os_booted = False
                        logger.info(f"OS booted {os_booted}")

                    wait_count += 1

        # Reset cycle loop
        if index == command_length:
            index = 0

        logger.info("*******************************************************")
        logger.info(
            f"************** Power Cycle Count {cycle_count} on {bmc_ip} ***************")
        logger.info("*******************************************************")

        # Calculate each cycle duration
        cycle_end_time = datetime.now()
        td = (cycle_end_time - cycle_time_start).total_seconds() * 10**3
        logger.info(
            f"The time of execution of one cycle is : {td:.03f}ms, {math.trunc(td / 60000)} minutes.")

        so_far_run = datetime.now()
        so_far_end_time = (so_far_run - test_start_time).total_seconds() * 10**3
        logger.info(f"\n  Test run time\
                    ************** {math.trunc(so_far_end_time / 60000)} min.\n\
                    {math.trunc(so_far_end_time / 60000) / 60} hr/s. \
                        ***************")

        # Power cycle end
        test_end = (cycle_end_time - test_start_time).total_seconds() * 10**3
        logger.info(
            f"Target cycle, default 1000: {target_cycle}, cycle count {cycle_count}")
       
        # Stop test when target run time or target cycle reach
        if test_end >= test_target_run or target_cycle <= cycle_count:
            keep_calling = False
            logger.info(f"***************************************************\n\
                        ******* Test ENDED ********\n\
                        ****************************************************")

        cycle_count += 1

    # End of test
    end_time = datetime.now()
    test_end_time = (end_time - test_start_time).total_seconds() * 10**3
    logger.info("*******************************************************")
    logger.info(
        f"Power cycle test ended. {cycle_count - 1} cycles completed.")
    logger.info(
        f"Test ran {math.trunc(test_end_time)}ms, {math.trunc(test_end_time / 60000)}min.")
    logger.info("*************** Have a nice day ***********************")


if __name__ == "__main__":
    main()
