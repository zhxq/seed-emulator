#!/usr/bin/python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf, Cloud
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.raps import SoftEtherRemoteAccessProvider
from seedemu.compiler import Docker

emu1    = Emulator(name = "emu1")
emu2    = Emulator(name = "emu2")
cloud   = Cloud()
base1    = Base()
base2    = Base()
routing1 = Routing()
routing2 = Routing()
ebgp1    = Ebgp()
ebgp2    = Ebgp()
ibgp1    = Ibgp()
ibgp2    = Ibgp()
ospf1    = Ospf()
ospf2    = Ospf()
web1     = WebService()
web2     = WebService()
vpn      = SoftEtherRemoteAccessProvider()

###############################################################################

# Create an Internet Exchange
ix100 = cloud.createInternetExchange(100)


###############################################################################
# Create a transit AS (AS-150)

as150 = base1.createAutonomousSystem(150)
as151 = base2.createAutonomousSystem(151)

as150.createNetwork('net0')
as151.createNetwork('net0')

# Create a router
as150.createRouter('r1').joinNetwork('ix100').joinNetwork('net0')
as151.createRouter('r1').joinNetwork('ix100').joinNetwork('net0')

# Create a web host
as150.createHost('web1').joinNetwork('net0')
as151.createHost('web1').joinNetwork('net0')
web1.install('web1')
web2.install('web1')
emu1.addBinding(Binding('web1', filter = Filter(asn = 150, nodeName = 'web')))
emu2.addBinding(Binding('web1', filter = Filter(asn = 151, nodeName = 'web')))


ix100.getPeeringLan().enableRemoteAccess(vpn)

ebgp1.addPrivatePeerings(100, [150], [151], PeerRelationship.Peer)


###############################################################################
# Rendering

# Add cloud to both emulators first
# so that they know the existence of each other
emu1.addLayer(cloud)
emu2.addLayer(cloud)
emu1.addLayer(base1)
emu2.addLayer(base2)
emu1.addLayer(routing1)
emu2.addLayer(routing2)

emu1.addLayer(web1)
emu2.addLayer(web2)

emu1.render()
emu2.render()

emu1.addLayer(ibgp1)
emu2.addLayer(ibgp2)
emu1.addLayer(ospf1)
emu2.addLayer(ospf2)
emu1.addLayer(ebgp1)
emu2.addLayer(ebgp2)

emu1.render()
emu2.render()

###############################################################################
# Compilation 

emu1.compile(Docker(), './output1', override=True)
emu2.compile(Docker(), './output2', override=True)
