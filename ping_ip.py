import subprocess

# ip_address = "10.244.16.77"
# duration = 2

def ping_ip(ip_address: str, duration: int) -> bool:
    """
    Function to ping a specific IP address with a small duration.

    Parameters:
    - ip_address: str
        The IP address to ping.
    - duration: int
        The duration in seconds for the ping command to run.

    Returns:
    - bool:
        True if the ping was successful, False otherwise.

    Raises:
    - ValueError:
        Raises an error if the IP address is not valid or the duration is not a positive integer.
    """

    # Validating the IP address format
    if not is_valid_ip(ip_address):
        raise ValueError("Invalid IP address format.")

    # Validating the duration
    if not isinstance(duration, int) or duration <= 0:
        raise ValueError("Duration should be a positive integer.")

    # Running the ping command
    try:
        output = subprocess.check_output(
            ["ping", "-c", "1", "-W", str(duration), ip_address])
        return True
    except subprocess.CalledProcessError:
        return False


def is_valid_ip(ip_address: str) -> bool:
    """
    Function to check if an IP address is valid.

    Parameters:
    - ip_address: str
        The IP address to validate.

    Returns:
    - bool:
        True if the IP address is valid, False otherwise.
    """

    # Splitting the IP address into octets
    octets = ip_address.split(".")

    # Validating the number of octets
    if len(octets) != 4:
        return False

    # Validating each octet
    for octet in octets:
        if not octet.isdigit() or int(octet) < 0 or int(octet) > 255:
            return False

    return True

# Example usage of the ping_ip function:
# ip_address = "10.244.16.136"
# duration = 1
# print(ping_ip(ip_address, duration))
# try:
#     result = ping_ip(ip_address, duration)
#     if result:
#         print(f"Ping to {ip_address} was successful.")
#     else:
#         print(f"Ping to {ip_address} failed.")
# except ValueError as e:
#     print(f"Error: {e}")
