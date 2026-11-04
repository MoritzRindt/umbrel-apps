# Private Umbrel App Store

Prepared for umbrelOS 2.0.1 on ARM64 Raspberry Pi 4. This directory is a standalone
community-store package; it is not the old HomeDeck runtime.

## FR24 Feeder

The package uses maintained upstream multi-architecture images, pinned by manifest
digest. It launches only their decoder/feeder binaries; their bundled map, graph
collection, automatic updates and other forwarding services are not started.

- `receiver`: readsb, the sole owner of the known RTL2838 (`0bda:2838`) USB device.
- `feeder`: FR24 binary with Beast TCP input from `receiver:30005`; no USB access.
- `server`: password-style sharing-key form and status page protected by Umbrel login.
- Receiver JSON is in a 16 MB tmpfs. Only the configuration and monitor are on SD.
- No host ports, Docker socket, privileged containers, host networking or media mounts.
- `exports.sh` maps the exact matching USB node; without a receiver it maps `/dev/null`.
  Restart the app after inserting/reinserting the receiver to discover its current node.
- Config updates are atomic, mode `0600`; keys are not returned by the status API.
- Native feeder output is suppressed so it cannot leak a key or exact location into
  container logs. Connection state is read from the private monitor file.
- First setup starts the waiting feeder automatically; after a key change restart the app.

## Verification

```bash
python3 -m unittest discover -s umbrel-app-store/moritz-fr24 -p 'test_*.py'
bash -n umbrel-app-store/moritz-fr24/exports.sh
```

Prepared, not yet deployed or hardware-verified. Before installation, verify both
upstream binaries start with all capabilities dropped, the receiver can claim USB,
FR24 writes the expected monitor format and both services recover after reboot.
Plex and Home Assistant are installed independently from the official store.

## Distribution

Umbrel community stores consume a separate Git repository with
`umbrel-app-store.yml` at its root. Do not publish this entire private HomeDeck
repository or put sharing keys, exact receiver coordinates or MCP tokens in the store.
The store has not yet been published. Adding a community store is an owner action;
the current Umbrel MCP tool set has no add-repository tool.
