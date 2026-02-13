from NwUtilties import NwUtilities
import sys
from configparser import ConfigParser
from pprint import pprint as pp


def main():
    nw = NwUtilities()
    hostname = nw._get_config('lab_device', 'host_ip')
    username = nw._get_config('lab_device', 'username')
    password = nw._get_config('lab_device', 'password')
    print(f'Connect to {hostname} -- {username}')
    dev = nw.junos_open_connection(hostname=hostname, username=username, password=password)
    pp(dev.facts)
    nw.junos_close_connection()
    print(f'Disconnected from {dev.hostname}')


def main1():
    nw = NwUtilities()
    try:
        dev = nw.junos_open_connection()
        print(f'Connected to {dev.hostname}')
        nw.junos_close_connection()
    except Exception as err:
        print(f"An error occurred: {err}")
        sys.exit(1)
    print(dev.facts)
    try:
        nw.junos_close_connection()
        print(f'Disconnected from {dev.hostname}')
    except Exception as err:
        print(f"An error occurred: {err}")

def main2():
    config = ConfigParser()
    config.read('./_config.ini')
    nw = NwUtilities(username=config["jumphost"]["username"], password=config["jumphost"]["password"],
                     hostname=config["jumphost"]["jump"], port=config["jumphost"]["port"])
    try:
        client = nw.jumphost_connect()
        stdin, stdout, stderr = client.exec_command("pwd")
        print(stdout.read().decode('utf-8').strip())
        client.close()
    except Exception as err:
        print(f"An error occurred: {err}")
        sys.exit(1)


if __name__ == '__main__':
    main()
    # main1()
    # main2()
