#!/usr/bin/env python3

# kde_sms.py - Send dad jokes on a somewhat regular basis

import subprocess
import requests
from bs4 import BeautifulSoup

class SMS:
    """
    SMS - Send SMS messages using KDE Connect CLI

    Attributes:
        _device_id (str): Device ID of the phone to send SMS messages.
        _contacts (dict): Dictionary mapping contact names to phone numbers.

    Properties:
        device_id (str): Device ID of the phone to send SMS messages.
        contacts (dict): Dictionary mapping contact names to phone numbers.

    Methods:
        send(str, str): Send an SMS message to a contact.
    """

    def __init__(self, dev_id=None):
        """
        Initialize SMS object with device ID and contacts dictionary.

        Args:
            dev_id (str): Device ID of the phone according to kdeconnect.
            contacts (dict): Dictionary mapping contact names to phone numbers.
        """
        self._device_id = dev_id
        self._contacts = {'muru': '6048359467', 'me': '6042265455'}

    @property
    def device_id(self):
        """
        Device ID of the phone according to kdeconnect.
        """
        if not self._device_id:
            dev_id_process = subprocess.run(
                'kdeconnect-cli -l --id-only',
                shell=True,
                capture_output=True,
                text=True
            )
            if dev_id_process.returncode == 0:
                self._device_id = dev_id_process.stdout.strip()
            else:
                raise Exception(dev_id_process.stderr.strip())
        return self._device_id

    def send(self, msg, destination):
        """
        Send an SMS message to a contact.

        Args:
            msg (str): SMS message to send.
            destination (str): Contact name or number to send SMS message to.
        Returns:
            int: Return code of the subprocess.
        """
        destination_number = self._contacts.get(destination)
        if not destination_number:
            raise ValueError(f"Invalid destination: {destination}")

        print(f'\033[33mAttempting send \033[0m \033[36m{msg}\033[0m] to \033[0m \033[36m{destination_number}\033[0m]...')
        send_sms_process = subprocess.run(
            f'kdeconnect-cli --send-sms "{msg}" --destination {destination_number} -d {self.device_id}',
            shell=True,
            capture_output=True,
            text=True
        )
        return send_sms_process.returncode
    
    @property
    def contacts(self):
        """
        Dictionary mapping contact names to phone numbers.
        """
        return self._contacts

    @contacts.setter
    def contacts(self, contacts):
        """
        Set the contacts dictionary.

        Args:
            contacts (dict): Dictionary mapping contact names to phone numbers.
        """
        self._contacts = contacts
    
    def __str__(self):
        """
        Return string representation of SMS object.
        """
        return str(self.__dict__)




# Example usage
def main():
    def joke():
        return subprocess.run(f'curl {url}', shell=True, capture_output=True, text=True)

    com = SMS('d847bc89_cacd_4cb7_855b_9570dba7d6fa')
    url = "https://icanhazdadjoke.com"
    try:
        msg = joke()
        if msg.returncode == 0:
            print(f'\033[32m{msg.stdout}\033[0m')
        elif msg.returncode == 1:
            print(f'\033[31m{msg.stdout}\033[0m')
        else:
            print(f'\033[31mERROR: \n{msg}\033[0m')


        print(f'\033[33m{com}\033[0m') # print SMS object (com)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()