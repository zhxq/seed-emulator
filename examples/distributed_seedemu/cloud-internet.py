#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

# We need to store the layers to render after every emulator is created
emus: List[Emulator] = []
bases: List[Base] = []
routings: List[Routing] = []
webs: List[WebService] = []
ovpns: List[OpenVpnRemoteAccessProvider] = []
ses: List[SoftEtherRemoteAccessProvider] = []

# Create Cloud layer
cloud = Cloud()
# Create SoftEther RAP for ix100, and choose emu1 as the server
# All others emulators will become clients for ix100
se100 = SoftEtherRemoteAccessProvider(serverEmu="emu1")
ix100 = cloud.createInternetExchange(100)
ix100.getPeeringLan().enableRemoteAccess(se100)

# Create SoftEther RAP for ix101, and choose emu2 as the server
# All others emulators will become clients for ix101
# Choose to expose 11443 for port 443, and so on
se101 = SoftEtherRemoteAccessProvider(serverEmu="emu2", startPort_443=11443, startPort_5555=16555, startPort_992=11992)
ix101 = cloud.createInternetExchange(101)
ix101.getPeeringLan().enableRemoteAccess(se101)

# All layers should share these layers to promote inter-emulator peering
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
ACoeff = 3
BCoeff = 3
CCoeff = 2
DCoeff = 10

round_start = 1
round_end = 4

for i in range(round_start, round_end):
    ###############################################################################
    emu     = Emulator(name="emu{}".format(i))
    emus.append(emu)
    base    = Base()
    bases.append(base)
    routing = Routing()
    routings.append(routing)
    
    web     = WebService()
    webs.append(web)
    #dhcp    = DHCPService()
    ovpn    = OpenVpnRemoteAccessProvider()
    ovpns.append(ovpn)
    
    A=ACoeff*i
    B=BCoeff*i
    C=CCoeff*i
    D=DCoeff*(i-1)

    ###############################################################################

    
    ix102 = cloud.createInternetExchange(102+A)
    ix103 = cloud.createInternetExchange(103+A)
    ix104 = cloud.createInternetExchange(104+A)

    ###############################################################################
    # Create Transit Autonomous Systems 

    ## Tier 1 ASes
    Makers.makeTransitAs(base, 2+B, [100, 101, 102+A], 
        [(100, 101), (101, 102+A)] 
    )

    Makers.makeTransitAs(base, 3+B, [100, 103+A, 104+A], 
        [(100, 103+A), (103+A, 104+A)]
    )

    Makers.makeTransitAs(base, 4+B, [100, 102+A, 104+A], 
        [(100, 104+A), (102+A, 104+A)]
    )

    ## Tier 2 ASes
    Makers.makeTransitAs(base, 51+C, [102+A, 103+A], [(102+A, 103+A)])
    Makers.makeTransitAs(base, 52+C, [101, 104+A], [(101, 104+A)])


    ###############################################################################
    # Create single-homed stub ASes. "None" means create a host only 

    Makers.makeStubAs(emu, base, 165+D, 100, [web, None])
    Makers.makeStubAs(emu, base, 166+D, 100, [web, None, None])

    Makers.makeStubAs(emu, base, 167+D, 101, [None, None])
    Makers.makeStubAs(emu, base, 168+D, 101, [web, None, None])

    Makers.makeStubAs(emu, base, 169+D, 102+A, [None, web])

    Makers.makeStubAs(emu, base, 170+D, 103+A, [web, None])
    Makers.makeStubAs(emu, base, 171+D, 103+A, [web, None, None])
    Makers.makeStubAs(emu, base, 172+D, 103+A, [web, None])

    Makers.makeStubAs(emu, base, 173+D, 104+A, [web, None])
    Makers.makeStubAs(emu, base, 174+D, 104+A, [None, None])

    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
    # which means each AS will only export its customers and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 

    ebgp.addRsPeers(102+A, [2+B, 4+B])
    ebgp.addRsPeers(104+A, [3+B, 4+B])

    # To buy transit services from another autonomous system, 
    # we will use private peering

    # For ix100 and 101, we want to peer to other ASes in different emulators
    for j in range(i, round_end):
        BB = j * ACoeff
        CC = j * CCoeff
        DD = DCoeff*(j-1)
        print("Added:")
        ebgp.addPrivatePeering(100, 2+B, 3+BB, PeerRelationship.Peer)
        print("{} <---> {}".format(2+B, 3+BB))
        ebgp.addPrivatePeering(100, 3+B, 4+BB, PeerRelationship.Peer)
        print("{} <---> {}".format(3+B, 4+BB))
        ebgp.addPrivatePeering(100, 2+B, 4+BB, PeerRelationship.Peer)
        print("{} <---> {}".format(2+B, 4+BB))
        ebgp.addPrivatePeerings(100, [2+B],  [165+DD, 166+DD], PeerRelationship.Provider)
        print("{} <---> {}, {}".format(2+B, 165+DD, 166+DD))
        ebgp.addPrivatePeerings(100, [3+B],  [165+DD], PeerRelationship.Provider)
        print("{} <---> {}".format(3+B, 165+DD))
        ebgp.addPrivatePeerings(101, [2+B],  [52+CC], PeerRelationship.Provider)
        print("{} <---> {}".format(2+B, 52+CC))
        ebgp.addPrivatePeerings(101, [52+C], [167+DD, 168+DD], PeerRelationship.Provider)
        print("{} <---> {}, {}".format(52+C, 167+DD, 168+DD))

    ebgp.addPrivatePeerings(102+A, [2+B, 4+B],  [51+C, 169+D], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102+A, [51+C], [169+D], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(103+A, [3+B],  [170+D, 171+D, 172+D ], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(104+A, [3+B, 4+B], [52+C], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104+A, [4+B],  [173+D], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104+A, [52+C], [174+D], PeerRelationship.Provider)

    ###############################################################################
    base.setNameServers(['10.153.0.53'])

    # Add layers to the emulator
    emu.addLayer(cloud)
    emu.addLayer(base)
    emu.addLayer(routing)
    #emu.addLayer(dhcp)


# First round render, to create node objects
# After this, we can perform inter-emulator BGP
for i in range(len(emus)):
    emu = emus[i]
    emu.render()

# Second round render - render all other layers
for i in range(len(emus)):
    emu = emus[i]
    emu.addLayer(webs[i])
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(ebgp)
    emu.render()
    print(emu.getName())
    #print(dns.getZone('.').getRecords())
    emu.compile(Docker(), './emus/output_'+str(i + 1), override=True)

