#!/usr/bin/python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.raps import SoftEtherRemoteAccessProvider
from seedemu.compiler import Docker

emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
web     = WebService()
vpn    = SoftEtherRemoteAccessProvider()

###############################################################################

# Create an Internet Exchange
ix100 = base.createInternetExchange(100)


###############################################################################
# Create a transit AS (AS-150)

as150 = base.createAutonomousSystem(150)

as150.createNetwork('net0')

# Create a router
as150.createRouter('r1').joinNetwork('ix100').joinNetwork('net0')

# Create a web host
as150.createHost('web1').joinNetwork('net0')
web.install('web1')
emu.addBinding(Binding('web1', filter = Filter(asn = 150, nodeName = 'web')))
print(as150.print(4))

ix100.getPeeringLan().enableRemoteAccess(vpn)
print(ix100.print(4))
#as150.getNetwork('net0').enableRemoteAccess(vpn)
###############################################################################
# Rendering

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

emu.render()

###############################################################################
# Compilation 

emu.compile(Docker(), './output', override=True)
