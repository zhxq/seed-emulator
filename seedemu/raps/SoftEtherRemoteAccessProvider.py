from seedemu.core import RemoteAccessProvider, Emulator, Network, Node
from seedemu.core.enums import NodeRole, NetworkType
from typing import Dict
from itertools import repeat

SoftEtherRapFileTemplates: Dict[str, str] = {}

SoftEtherRapFileTemplates['se_server_build_script'] = '''\
#!/bin/bash
mkdir -p /vpn
cd /vpn
git clone https://github.com/SoftEtherVPN/SoftEtherVPN.git
cd SoftEtherVPN
git submodule init && git submodule update
./configure
make -C build
make -C build install
'''

SoftEtherRapFileTemplates['se_server_startup_script'] = '''\
#!/bin/bash
echo "VPN server ready! run 'docker exec -it $HOSTNAME /bin/bash' to attach to this VPN server" >&2
vpnserver start
sleep 5
vpncmd localhost:443 /SERVER /ADMINHUB:default /CMD BridgeCreate default /DEVICE:eth0 /TAP:no
vpncmd localhost:443 /SERVER /ADMINHUB:default /CMD UserCreate {username} /group:none /realname:none /note:none
vpncmd localhost:443 /SERVER /ADMINHUB:default /CMD UserAnonymousSet {username}
vpncmd localhost:443 /SERVER /ADMINHUB:default /CMD UserGet {username}
vpncmd localhost:443 /SERVER /ADMINHUB:default /CMD KeepEnable
'''

SoftEtherRapFileTemplates['se_client_connector'] = '''\
#!/bin/bash
if [[ -z $1 ]]; then
    echo "Please provide IP address for remote VPN server."
    exit
else
    export VPN_SERVER_ADDR=$1
fi

if [[ -z $2 ]]; then
    echo "Please provide port for remote VPN server."
    exit
else
    export VPN_SERVER_PORT=$2
fi
vpnbridge stop

'''

SoftEtherRapFileTemplates['se_client_startup_script'] = '''\
#!/bin/bash
echo "VPN client ready! run 'docker exec -it $HOSTNAME /bin/bash' to attach to this VPN client" >&2
vpnbridge start
sleep 5
vpncmd localhost:443 /SERVER /ADMINHUB:bridge /CMD BridgeCreate bridge /DEVICE:eth0 /TAP:no
vpncmd localhost:443 /SERVER /ADMINHUB:bridge /CMD CascadeCreate test /SERVER:$VPN_SERVER_ADDR:$VPN_SERVER_PORT /HUB:default /USERNAME:{username}
vpncmd localhost:443 /SERVER /ADMINHUB:bridge /CMD CascadeAnonymousSet test
vpncmd localhost:443 /SERVER /ADMINHUB:bridge /CMD CascadeOnline test
vpncmd localhost:443 /SERVER /ADMINHUB:bridge /CMD CascadeStatusGet test
'''

class SoftEtherRemoteAccessProvider(RemoteAccessProvider):

    __cur_port_443: int
    __cur_port_992: int
    __cur_port_5555: int
    __naddrs: int

    __ovpn_ca: str
    __ovpn_cert: str
    __ovpn_key: str


    def __init__(self, authMethod: str = None, username: str = "seed", ip: int = 2, startPort_443: int = 10443, startPort_992: int = 10992, startPort_5555: int = 15555):
        """!
        @brief SoftEther remote access provider constructor.

        if you do not set ca/cert/key, bulitin ones will be used. to connect, 
        use the client configuration under misc/ folder. 

        @param startPort (optional) port number to start assigning from for
        port fowarding to the open server. 
        @param naddrs number of IP addresses to assign to client pool.
        @param ovpnCa (optional) CA to use for openvpn.
        @param ovpnCert (optional) server certificate to use for openvpn.
        @param ovpnKey (optional) server key to use for openvpn.
        """
        super().__init__()

        self.__cur_port_443 = startPort_443
        self.__cur_port_992 = startPort_992
        self.__cur_port_5555 = startPort_5555
        
        self.__username = username
        self.__ip_end = ip
    def getName(self) -> str:
        return "SoftEtherClient"

    def configureRemoteAccess(self, emulator: Emulator, netObject: Network, brNode: Node, brNet: Network):
        self._log('setting up SoftEther remote access for {} in AS{}...'.format(netObject.getName(), brNode.getAsn()))

        brNode.addSoftware('apt-utils pkg-config curl cmake gcc g++ make libncurses5-dev libssl-dev libsodium-dev libreadline-dev zlib1g-dev build-essential dnsutils ipcalc iproute2 iputils-ping jq mtr-tiny nano netcat tcpdump termshark vim-nox git zsh')
        brNode.addSoftware('bridge-utils')
        #brNode.setFile('/softether_install', SoftEtherRapFileTemplates['se_server_build_script'])
        brNode.addBuildCommand("mkdir -p /vpn && cd /vpn && git clone https://github.com/SoftEtherVPN/SoftEtherVPN.git && cd SoftEtherVPN && git submodule init && git submodule update && ./configure && make -C build && make -C build install")

        brNode.setFile('/softether_server_startup', SoftEtherRapFileTemplates['se_server_startup_script'].format(
            username = self.__username
        ))

        brNode.setFile('/softether_connector', SoftEtherRapFileTemplates['se_client_connector'])
        brNode.setFile('/softether_client_startup', SoftEtherRapFileTemplates['se_client_startup_script'].format(
            username = self.__username
        ))
            
        # note: ovpn_startup will invoke interface_setup, and replace interface_setup script with a dummy. 
        brNode.appendStartCommand('chmod +x /softether_server_startup')
        brNode.appendStartCommand('chmod +x /softether_client_startup')
        brNode.appendStartCommand('chmod +x /softether_connector')
        brNode.appendStartCommand('/softether_server_startup')

        #if netObject.getType() != NetworkType.InternetExchange:
        #brNode.appendStartCommand('ip route add default via {} dev {}'.format(brNet.getPrefix()[1], brNet.getName()))
        brNode.joinNetwork(brNet.getName())
        self._log('Joining {}'.format(brNet.getName()))
        brNode.joinNetwork(netObject.getName(), netObject.getPrefix()[self.__ip_end])
        self._log('Joining {}'.format(netObject.getName()))

        brNode.addPort(self.__cur_port_443, 443)
        brNode.addPort(self.__cur_port_992, 992)
        brNode.addPort(self.__cur_port_5555, 5555)