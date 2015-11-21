# Copyright []
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
### BEGIN NODE INFO
[info]
name = IPS 120_10 Superconducting Magnet Power Supply
version = 1.0
description =
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import platform
global serial_server_name
serial_server_name = platform.node() + '_serial_server'

from labrad.server import setting
from labrad.devices import DeviceServer,DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import labrad.units as units
from labrad.types import Value

TIMEOUT = Value(5,'s')
BAUD    = 9600

class IPS120Wrapper(DeviceWrapper):

    @inlineCallbacks
    def connect(self, server, port):
        """Connect to a device."""
        print 'connecting to "%s" on port "%s"...' % (server.name, port),
        self.server = server
        self.ctx = server.context()
        self.port = port
        p = self.packet()
        p.open(port)
        print 'opened on port "%s"' %self.port
        p.baudrate(BAUD)
        p.read()  # clear out the read buffer
        p.timeout(TIMEOUT)
        print(" CONNECTED ")
        yield p.send()
        
    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)

    def shutdown(self):
        """Disconnect from the serial port when we shut down."""
        return self.packet().close().send()

    @inlineCallbacks
    def write(self, code):
        """Write a data value to the heat switch."""
        yield self.packet().write(code).send()

    @inlineCallbacks
    def read(self):
        p=self.packet()
        p.read_line()
        ans=yield p.send()
        returnValue(ans.read_line)

    @inlineCallbacks
    def query(self, code):
        """ Write, then read. """
        p = self.packet()
        p.write_line(code)
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)
        

class IPS120Server(DeviceServer):
    name = 'ips120_power_supply'
    deviceName = 'IPS120 Power Supply'
    deviceWrapper = IPS120Wrapper

    @inlineCallbacks
    def initServer(self):
        print 'loading config info...',
        self.reg = self.client.registry()
        yield self.loadConfigInfo()
        print 'done.'
        print self.serialLinks
        yield DeviceServer.initServer(self)

    @inlineCallbacks
    def loadConfigInfo(self):
        """Load configuration information from the registry."""
        # reg = self.client.registry
        # p = reg.packet()
        # p.cd(['', 'Servers', 'Heat Switch'], True)
        # p.get('Serial Links', '*(ss)', key='links')
        # ans = yield p.send()
        # self.serialLinks = ans['links']
        reg = self.reg
        yield reg.cd(['', 'Servers', 'IPS120', 'Links'], True)
        dirs, keys = yield reg.dir()
        p = reg.packet()
        print " created packet"
        print "printing all the keys",keys
        for k in keys:
            print "k=",k
            p.get(k, key=k)
            
        ans = yield p.send()
        print "ans=",ans
        self.serialLinks = dict((k, ans[k]) for k in keys)


    @inlineCallbacks
    def findDevices(self):
        """Find available devices from list stored in the registry."""
        devs = []
        # for name, port in self.serialLinks:
        # if name not in self.client.servers:
        # continue
        # server = self.client[name]
        # ports = yield server.list_serial_ports()
        # if port not in ports:
        # continue
        # devName = '%s - %s' % (name, port)
        # devs += [(devName, (server, port))]
        # returnValue(devs)
        for name, (serServer, port) in self.serialLinks.items():
            if serServer not in self.client.servers:
                continue
            server = self.client[serServer]
            print server
            print port
            ports = yield server.list_serial_ports()
            print ports
            if port not in ports:
                continue
            devName = '%s - %s' % (serServer, port)
            devs += [(devName, (server, port))]

       # devs += [(0,(3,4))]
        returnValue(devs)
    
    @setting(100)
    def connect(self,c,server,port):
        dev=self.selectedDevice(c)
        yield dev.connect(server,port)

    @setting(101, mode='i',returns='s')
    def set_control(self,c,mode):
        dev=self.selectedDevice(c)
        yield dev.write("C%i\r\n"%mode)
        ans = yield dev.read()
        returnValue(ans)

    @setting(102, comm='i')
    def set_comm_protocol(self,c,comm):
        dev=self.selectedDevice(c)
        yield dev.write("Q%i\r\n"%comm)

    @setting(103, parameter='i', returns='s')
    def read_parameter(self,c,parameter):
        dev=self.selectedDevice(c)
        yield dev.write("R%i\r\n"%parameter)
        ans = yield dev.read()
        returnValue(ans)

    @setting(104, key='i', returns='s')
    def unlock(self,c,key):
        dev=self.selectedDevice(c)
        yield dev.write("U%i\r\n"%key)
        ans = yield dev.read()
        returnValue(ans)

    @setting(105, returns='s')
    def version(self,c):
        dev=self.selectedDevice(c)
        yield dev.write("V\r\n")
        ans = yield dev.read()
        returnValue(ans)

    @setting(106, time='i', returns='s')
    def wait(self,c,time):
        dev=self.selectedDevice(c)
        yield dev.write("W%i\r\n"%time)
        ans = yield dev.read()
        returnValue(ans)

    @setting(107, returns='s')
    def status(self,c):
        dev=self.selectedDevice(c)
        yield dev.write("X\r\n")
        ans = yield dev.read()
        returnValue(ans)

    @setting(108, activity='i', returns='s')
    def set_activity(self,c,activity):
        dev=self.selectedDevice(c)
        yield dev.write("A%i\r\n"%activity)
        ans = yield dev.read()
        returnValue(ans)

    @setting(109, parameter='i', returns='s')
    def set_panelDisplay(self,c,parameter):
        dev=self.selectedDevice(c)
        yield dev.write("F%i\r\n"%parameter)
        ans = yield dev.read()
        returnValue(ans)

    @setting(110, mode='i', returns='s')
    def set_switchHeater(self,c,mode):
        dev=self.selectedDevice(c)
        yield dev.write("H%i\r\n"%mode)
        ans = yield dev.read()
        returnValue(ans)

    @setting(111, current='v', returns='s')
    def set_targetCurrent(self,c,current):
        dev=self.selectedDevice(c)
        yield dev.write("I%i\r\n"%current)
        ans = yield dev.read()
        returnValue(ans)

    @setting(112, field='v', returns='s')
    def set_targetField(self,c,field):
        dev=self.selectedDevice(c)
        yield dev.write("J%i\r\n"%field)
        ans = yield dev.read()
        returnValue(ans)

    @setting(113, mode='i', returns='s')
    def set_mode(self,c,mode):
        dev=self.selectedDevice(c)
        yield dev.write("M%i\r\n"%mode)
        ans = yield dev.read()
        returnValue(ans)

    @setting(114, polarity='i', returns='s')
    def set_polarity(self,c,polarity):
        dev=self.selectedDevice(c)
        yield dev.write("P%i\r\n"%polarity)
        ans = yield dev.read()
        returnValue(ans)

    @setting(115, rate='v', returns='s')
    def set_currentSweep_rate(self,c,rate):
        dev=self.selectedDevice(c)
        yield dev.write("S%i\r\n"%rate)
        ans = yield dev.read()
        returnValue(ans)

    @setting(116, rate='v', returns='s')
    def set_fieldSweep_rate(self,c,rate):
        dev=self.selectedDevice(c)
        yield dev.write("T%i\r\n"%rate)
        ans = yield dev.read()
        returnValue(ans)

    @setting(117, nKbytes='i', returns='s')
    def load_ram(self,c,nKbytes):
        dev=self.selectedDevice(c)
        yield dev.write("Y%i\r\n"%nKbytes)
        ans = yield dev.read()
        returnValue(ans)

    @setting(118, nKbytes='i', returns='s')
    def dump_ram(self,c,nKbytes):
        dev=self.selectedDevice(c)
        yield dev.write("Z%i\r\n"%nKbytes)
        ans = yield dev.read()
        returnValue(ans)

    
    @setting(9001,v='v')
    def do_nothing(self,c,v):
        pass

    @setting(9002)
    def read(self,c):
        dev=self.selectedDevice(c)
        ret=yield dev.read()
        returnValue(ret)

    @setting(9003)
    def write(self,c,phrase):
        dev=self.selectedDevice(c)
        yield dev.write(phrase)
    @setting(9004)
    def query(self,c,phrase):
        dev=self.selectedDevice(c)
        yield dev.write(phrase)
        ret = yield dev.read()
        returnValue(ret)

    
__server__ = IPS120Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)