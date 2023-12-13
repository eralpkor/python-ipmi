#!/usr/bin/python
from codetiming import Timer
import logging
import requests
import time
from datetime import datetime
import subprocess
import os
import config
import urllib3
import colorlog
import sys
import math
import ping_ip
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
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
bmc_ip = config.bmc_ip
user = config.bmc_user
password = config.bmc_pw
target_cycle = config.target_cycle
folder_path = ''
filename = ''
time_tag = datetime.now().strftime("%Y%m%d_%H%M%S.%f")
log_file = ''
test_log_path = 'logs/'
test_target_run = config.hours * 3600000
logger.warning(f"Test will run {math.trunc(test_target_run / 60000)} minutes")
test_start_time = datetime.now()

# Create log file
folder_path = test_log_path + time_tag + '_' + bmc_ip
try:
    os.makedirs(folder_path)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
log_file = folder_path + '/RunningLog_' + bmc_ip + '.txt'

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

# Example usage of the ping_ip function:
# ip_address = "10.244.16.0"
# duration = 1

# ping_ip.ping_ip(ip_address, duration)
if not ping_ip.ping_ip(bmc_ip, 2):
    logger.error(f"Cannot ping BMC ip {bmc_ip}")
    sys.exit(1)

# HTTP RedFish call to check system status


def system_status():
    try:
        r = session.get(rest_api, verify=False)
        status = r.json()["Oem"]["Lenovo"]["SystemStatus"]
        return status
    except requests.exceptions.RequestException as e:
        logger.error("Cannot connect to BMC, exiting.")
        raise sys.exit(e)


# Check system status before cycle test
status = system_status()
logger.info(f"System status {status}")
# Clear logs before running the script
# Clear Audit logs
a = session.post(rest_api +
                 '/LogServices/AuditLog/Actions/LogService.ClearLog', json=post_data, verify=False)
logger.info("Audit logs cleared.")
# Clear SEL logs
s = session.post(rest_api + '/LogServices/SEL/Actions/LogService.ClearLog',
                 json=post_data, verify=False)
logger.info("SEL logs cleared.")
# Clear Event logs
e = session.post(rest_api + '/LogServices/PlatformLog/Actions/LogService.ClearLog',
                 json=post_data, verify=False)
logger.info("Event logs cleared.")


# def ping(bmc_ip):
#     return not os.system('ping %s -n 1' % (bmc_ip,))  # Windows
# return not os.system('ping %s -c 1' % (bmc_ip,)) # Linux
# def ping(bmc_ip):
#     logger.info(f"Pinging {bmc_ip}")
#     res = subprocess.run(["ping", "-n", "1", str(bmc_ip)])  # Windows
#     # res = subprocess.run(["ping", "-c", "1", str(bmc_ip)]) # Linux
#     return res.returncode == 0


ipmiCommand = [
    ["0x00", "0x02", "0x00"],
    ["0x00", "0x02", "0x01"],
    ["0x00", "0x02", "0x02"],
    ["0x00", "0x02", "0x03"]]

ipmi_power = ["off", "on", "cycle", "reset"]

# Windows only
ipmi_path = 'C:\\python-ipmi\\ipmi\\'
ipmi_cmd = 'ipmitool.exe'
command_length = len(ipmiCommand)


# ipmitool
def ipmi_cycle(ip_address, a, b, c):
    try:
        subprocess.run(
            f"{ipmi_path}{ipmi_cmd} -I lanplus -C 17 -H {ip_address} -U {user} -P {password} raw {a} {b} {c}", shell=True, stdout=None, stderr=None)
        logger.info(stdout)
        time.sleep(10)
        logger.info(f"ipmi raw command sent {a}, {b}, {c}")

    except Exception as e:
        # Log the error
        logger.critical(f"Error: {e}")
        return "An error occurred"


def main():
    is_system_busy = False
    index = 0
    os_booted = False
    keep_calling = True
    command = []
    cycle_count = 1
    logger.info(f"************* Cycle test start {datetime.now()} ***********")

    while keep_calling:
        is_powered_off = False
        status = system_status()
        logger.info(f"********** Power Cycle {cycle_count} start. ***********")
        if status == "SystemPowerOff_StateUnknown":
            is_powered_off = True
        logger.info(f"is powered off {is_powered_off}")
        cycle_time_start = datetime.now()
        for raw in ipmiCommand:
            logger.info(f"is system busy {is_system_busy}")
            command = raw  # type: ignore
            status = system_status()
            logger.info(f"Status {status}")
            if status == "SystemOn_StartingUEFI" or \
                    status == "SystemRunningInUEFI" or \
                    status == "BootingOSOrInUndetectedOS":
                is_system_busy = True
                logger.info(f"System busy {is_system_busy}")

            wait_count = 1

            # Wait until next ipmi command
            while is_system_busy:
                logger.warning(f"Wait count {wait_count}")
                if wait_count > 20:
                    logger.critical(
                        f"Waited 20 minutes System state did not change. Exiting test {system_status()}")
                    sys.exit(1)

                logger.info("Sleeping 20 seconds to detect power state.")
                time.sleep(20)
                status = system_status()
                logger.info(f"System status: {status}")
                # Check redFish state, if not OS booted or powered off keep checking
                if status == "OSBooted" or \
                        status == "SystemPowerOff_StateUnknown":
                    is_system_busy = False
                    logger.warning(f"Is system busy booting {is_system_busy}")
                wait_count += 1

            logger.info(f"Sleep 20 Seconds before raw command {command}")
            time.sleep(20)

            ipmi_cycle(bmc_ip, command[0], command[1], command[2])
            logger.warning(f"ipmi power {ipmi_power[index]} command sent.")
            is_system_busy = True
            logger.info(f"is system busy {is_system_busy}")

            # Check if ipmi off command turned off the system
            if command[2] == "0x00":
                wait_count = 1
                logger.info(f"Shut down wait count {wait_count}")
                while not is_powered_off:
                    status = system_status()
                    if wait_count > 30:
                        logger.critical(
                            f"Waited 10 minutes but System did not power off, test exited. Power status {status}")
                        sys.exit(1)

                    logger.info(
                        "Sleep 20 seconds to check if system powered off.")
                    time.sleep(20)
                    status = system_status()
                    logger.info(f"System status {status}")

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
                    if wait_count > 30:
                        logger.critical(
                            f"Waited 10 minutes, but system did not power on {status}")
                        sys.exit(1)

                    logger.info(
                        "Sleep 20 seconds to check if system powered on.")
                    time.sleep(20)
                    status = system_status()
                    logger.info(f"System status {status}")

                    if status == "OSBooted":
                        os_booted = True
                        logger.info(f"OS booted {os_booted}")
                    else:
                        os_booted = False
                        logger.info(f"OS booted {os_booted}")

                    wait_count += 1

        # Reset cycle loop
        if index == command_length:
            index = 0

        logger.info("*******************************************************")
        logger.info(
            f"************** Power Cycle Count {cycle_count} ***************")
        logger.info("*******************************************************")

        # Calculate each cycle duration
        cycle_end_time = datetime.now()
        td = (cycle_end_time - cycle_time_start).total_seconds() * 10**3
        logger.info(
            f"The time of execution of one cycle is : {td:.03f}ms, {math.trunc(td / 60000)} minutes.")

        # Power cycle end
        test_end = (cycle_end_time - test_start_time).total_seconds() * 10**3
        logger.warning(
            f"Target cycle: {target_cycle}, cycle count {cycle_count}")
        logger.warning(
            f"What's test end {math.trunc(test_end / 60000)} min., what's test run time {test_target_run / 60000} min.")
        logger.warning(
            f"Target cycle {target_cycle} cycle count {cycle_count}")
        # Stop test when target run time or target cycle reach
        if test_end >= test_target_run or target_cycle <= cycle_count:
            keep_calling = False
            logger.error(f"Whats keep calling {keep_calling}")

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
