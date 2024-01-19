# Python ipmitool power cycle script

### This script uses Intelligent Platform Management Interface (IPMI) and RedFish api to do power cycle test on servers with BMC. Script constantly checks the system power status with RedFish api to do maximum power cycles in giving time on the server.

### Usage:

-- On Windows system you need Windows ipmitool.exe installed </br>
-- Linux systems comes with ipmitool or install it from depository

install requirements:
$ pip install -r requirements.txt

-- Running the code
-- cycle.py takes seven arguments that is required:

You need to put timer/duration in hours if you need to run it so many hours, you also need to put cycle amount. Default cycle amount is 200 proximately 12 hours and depends on the server boot time.

## Example

-- python cycle.py [Options]

`python cycle.py -u USERID -p Password -i 192.168.0.123 -c 17 -t 12 -m 200 -l filename`

```
"h" or "--help" to see menu
"-u" or "--username", "BMC user name"
"-p" or "--password", "BMC password"
"-i" or "--ipaddress", "BMC ip address"
"-c" or "--cipher", "BMC security cipher"
"-l" or "--log", "Log file name"
"-t" or "--timer", "Test running time in hours"
"-m" or "--target", "How many cycles to run, default is 200"
```
