"""IPFabric API integration."""

import logging

from ipfabric_diagrams import IPFDiagram
from ipfabric import IPFClient

EMPTY = "(empty)"

# Default IP Fabric API pagination limit
DEFAULT_PAGE_LIMIT = 100
LAST = "$last"
PREV = "$prev"
LAST_LOCKED = "$lastLocked"

# URLs
INVENTORY_DEVICES_URL = "tables/inventory/devices"
INTERFACE_LOAD_URL = "tables/interfaces/load"
INTERFACE_ERRORS_URL = "tables/interfaces/errors/bidirectional"
INTERFACE_DROPS_URL = "tables/interfaces/drops/bidirectional"
BGP_NEIGHBORS_URL = "tables/routing/protocols/bgp/neighbors"
WIRELESS_SSID_URL = "tables/wireless/radio"
WIRELESS_CLIENT_URL = "tables/wireless/clients"
ADDRESSING_HOSTS_URL = "tables/addressing/hosts"

# COLUMNS
INVENTORY_COLUMNS = [
    "hostname",
    "siteName",
    "vendor",
    "platform",
    "model",
    "memoryUtilization",
    "version",
    "sn",
    "loginIp",
]
DEVICE_INFO_COLUMNS = ["hostname", "siteName", "vendor", "platform", "model"]
INTERFACE_LOAD_COLUMNS = ["intName", "inBytes", "outBytes"]
INTERFACE_ERRORS_COLUMNS = ["intName", "errPktsPct", "errRate"]
INTERFACE_DROPS_COLUMNS = ["intName", "dropsPktsPct", "dropsRate"]
BGP_NEIGHBORS_COLUMNS = [
    "hostname",
    "localAs",
    "srcInt",
    "localAddress",
    "vrf",
    "neiHostname",
    "neiAddress",
    "neiAs",
    "state",
    "totalReceivedPrefixes",
]
WIRELESS_SSID_COLUMNS = [
    "wlanSsid",
    "siteName",
    "apName",
    "radioDscr",
    "radioStatus",
    "clientCount",
]
WIRELESS_CLIENT_COLUMNS = [
    "controller",
    "siteName",
    "apName",
    "client",
    "clientIp",
    "ssid",
    "rssi",
    "signalToNoiseRatio",
    "state",
]
ADDRESSING_HOSTS_COLUMNS = [
    "ip",
    "vrf",
    "dnsName",
    "siteName",
    "edges",
    "gateways",
    "accessPoints",
    "mac",
    "vendor",
    "vlan",
]

# Filters
EQ = "ieq"

# Sort
INTERFACE_SORT = {"order": "desc", "column": "intName"}

logger = logging.getLogger("rq.worker")


# pylint: disable=R0904, disable=R0903
class IpFabric:
    """IpFabric will provide a wrapper for python-ipfabric clients that contain all the necessary API methods."""

    def __init__(self, base_url, token, verify=False, timeout=10):
        """Initialise the IP Fabric wrapper object to provide access to the client and diagram API from the python-ipfabric library.

        Args:
            base_url (str): URL of the IP Fabric host.
            token (str): API token for the IP Fabric client to access the server.
            verify (bool, optional): Verify identity of requested host when using HTTPS. Defaults to False. Enable with verify='path/to/client.pem'.
            timeout (int, optional): HTTP timeout connection (seconds). Defaults to 10.
        """
        self.client = IPFClient(
            base_url=base_url,
            token=token,
            verify=verify,
        )
        self.diagram = IPFDiagram(
            base_url=base_url,
            token=token,
            verify=verify,
            timeout=timeout,
        )

    def get_formatted_snapshots(self):
        """Get all snapshots and format them for display in chatops choice menu.

        Returns:
            list: Snapshot objects as tuple (description, snapshot_id)
        """
        formatted_snapshots = {}
        snapshot_refs = []
        for snapshot_ref, snapshot in self.client.snapshots.items():
            if snapshot.state != "loaded":
                continue
            description = "🔒 " if snapshot.locked else ""
            if snapshot_ref in [LAST, PREV, LAST_LOCKED]:
                description += f"{snapshot_ref}: "
                snapshot_refs.append(snapshot_ref)
            if snapshot.name:
                description += snapshot.name + " - " + snapshot.end.strftime("%d-%b-%y %H:%M:%S")
            else:
                description += snapshot.end.strftime("%d-%b-%y %H:%M:%S") + " - " + snapshot.snapshot_id
            formatted_snapshots[snapshot_ref] = (description, snapshot.snapshot_id)
        for ref in snapshot_refs:
            formatted_snapshots.pop(formatted_snapshots[ref][1], None)
        snapshot_table = [
            (
                snap_id,
                self.client.snapshots[snap_id].name or EMPTY,
                self.client.snapshots[snap_id].start.strftime("%d-%b-%y %H:%M:%S"),
                self.client.snapshots[snap_id].end.strftime("%d-%b-%y %H:%M:%S"),
                self.client.snapshots[snap_id].count,
                self.client.snapshots[snap_id].licensed_count,
                str(self.client.snapshots[snap_id].locked),
                self.client.snapshots[snap_id].version or EMPTY,
                getattr(self.client.snapshots[snap_id], "note", None) or EMPTY,  # TODO: Note being added to ipf v5.0
            )
            for snap_id in formatted_snapshots.keys()
        ]
        return list(formatted_snapshots.values()), snapshot_table
