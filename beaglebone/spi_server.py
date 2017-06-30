# Created by Carlos Kometter
# Last modified 3/30/2017

from bbio import *
from bbio.platform.beaglebone.spi import SPIBus
from labrad.server import LabradServer, setting
from labrad.errors import Error
from labrad.errors import DeviceNotSelectedError
import labrad.units as units
from twisted.internet.defer import inlineCallbacks
from twisted.internet.reactor import callLater
from twisted.internet.defer import inlineCallbacks

"""
### BEGIN NODE INFO
[info]
name = SPI Bus
version = 1.0.0-no-refresh
description = Gives access to SPI devices via pybbio.
instancename = %LABRADNODE% SPI Bus

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

# Format (IDA#, IDB#) where # is the slot number and is in ascending order.
ID_PINS = [(GPIO2_6, GPIO2_7),
           (GPIO2_15, GPIO2_12),
           (GPIO0_10, GPIO0_11),
           (GPIO1_1, GPIO1_0),
           (GPIO0_27, GPIO2_1),
           (GPIO2_4, GPIO1_13),
           (GPIO1_6, GPIO1_7),
           (GPIO3_19, GPIO3_17),
           (GPIO1_18, GPIO1_16)]

DEVICES_ID = {(LOW, LOW): 'NC',
              (LOW, HIGH): 'DAC',
              (HIGH, LOW): 'ADC',
              (HIGH, HIGH): 'TBD'}

# #Format {dedicated chip select: spi mode}
# SPI_MODE = {1: 0,
#             3: 1}


class SPISlot(SPIBus):
    def __init__(self, slot, type):
        self.slot = slot
        self.type = type
        self.dedicated_cs = None
        self.chip_selects = {}

    def set_chip_selects(self):
        "TODO"

    def get_chip_select(self, cs):
        "TODO"

    def get_type(self):
        return self.type

    def set_dedicated_cs(self, cs):
        self.dedicated_cs = cs

    def get_dedicated_cs(self):
        return self.dedicated_cs


class SPIBusServer(LabradServer):

    name = '%LABRADNODE% SPI Bus'

    refreshInterval = 10
    defaultTimeout = 1.0 * units.s

    def initServer(self):
        self.devices = {}
        self.configure_id_pins()
        self.bus = SPI0
        self.bus.open()
        # start refreshing only after we have started serving
        # this ensures that we are added to the list of available
        # servers before we start sending messages
        callLater(0.1, self.startRefreshing)

    def configure_id_pins(self):
        for slot in range(0, 8):
            pinMode(ID_PINS[slot][0], INPUT)
            pinMode(ID_PINS[slot][1], INPUT)

    def startRefreshing(self):
        """Start periodically refreshing the list of devices.

        The start call returns a deferred which we save for later.
        When the refresh loop is shutdown, we will wait for this
        deferred to fire to indicate that it has terminated.
        """
        # self.refresher = LoopingCall(self.refreshDevices)
        # self.refresherDone = self.refresher.start(self.refreshInterval, now=True)
        self.refreshDevices()

    @inlineCallbacks
    def stopServer(self):
        """Kill the device refresh loop and wait for it to terminate."""
        if hasattr(self, 'refresher'):
            self.refresher.stop()
            yield self.refresherDone

    def refreshDevices(self):
        """
        Refresh the list of known devices on this bus.
        """

        try:
            print 'Refreshing devices:'
            devices = self.list_devices()
            slots_available = [x[0] for x in devices]
            additions = set(slots_available) - set(self.devices.keys())
            updates = set()
            for x in (set(slots_available) - additions):
                if x[1] != self.devices[x[0]]:
                    updates.add(x)
            modifications = additions | updates
            deletions = set(self.devices.keys()) - set(slots_available)
            for device in devices:
                if device[0] in modifications:
                    try:
                        self.devices[device[0]] = SPISlot(device[0], device[1])
                        self.sendDeviceMessage('SPI Device Connect', str(device[0]))
                    except Exception, e:
                        print 'Failed to add ' + str(device[0]) + ':' + str(e)
                if device[0] in deletions:
                    del self.devices[device[0]]
                    self.sendDeviceMessage('SPI Device Disconect', str(device[0]))
        except Exception, e:
            print 'Problem while refreshing devices:', str(e)

    def sendDeviceMessage(self, msg, addr):
        print msg + ': ' + addr
        self.client.manager.send_named_message(msg, (self.name, addr))

    def list_devices(self):
        devices = []
        for slot in range(0, 8):
            ida = digitalRead(ID_PINS[slot][0])
            idb = digitalRead(ID_PINS[slot][1])
            if DEVICES_ID[(ida, idb)] != 'NC':
                devices.append((slot, DEVICES_ID[(ida, idb)]))
        return devices

    def getDevice(self, c):
        if 'slot' not in c:
            raise DeviceNotSelectedError("No SPI slot selected")
        if c['slot'] not in self.devices:
            raise Exception('Could not find device ' + c['slot'])
        device = self.devices[c['slot']]
        return device

    @setting(0, slot='w', returns='w')
    def slot(self, c, slot=None):
        """Get or set the SPI slot for this context.

        To get the slot of available devices,
        use the list_devices function.
        """
        if slot is not None:
            c['slot'] = slot
        return c['slot']

    @setting(1, 'List Spi Devices', returns=['*(s,s): List of spi devices'])
    def list_spi_devices(self, c):
        """Retrieves a list of all spi devices.

        NOTES:
        This list contains all devices connected,
        including ones that are already in use by other programs."""
        print self.devices
        device_list = [(slot, self.devices[slot]) for slot in range(0, 8)]
        return device_list

    @setting(2)
    def refresh_devices(self, c):
        """ manually refresh devices """
        self.refreshDevices()

    @setting(3, 'Transfer', cs=['s: chip select to send the data'],
             data=['*w: List of bytes to send'],
             returns=['*w: List of received bytes'])
    def transfer(self, c, cs, data):
        """Sends data"""
        device = self.getDevice(c)
        chip_select = device.get_chip_select(cs)
        dedicated_cs = device.dedicated_cs()
        digitalWrite(chip_select, LOW)
        ans = SPI0.transfer(dedicated_cs, data)
        digitalWrite(chip_select, HIGH)
        return ans


__server__ = SPIBusServer()
if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
