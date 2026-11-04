# Umbrel Community Apps

Community app packages for umbrelOS 2.0 and later, with an isolated ADS-B feeder.
This integration is not affiliated with or endorsed by Flightradar24 or Umbrel.

## Add this store

In Umbrel's App Store, open Community App Stores and add:

`https://github.com/MoritzRindt/umbrel-apps`

Install **FR24 Feeder**, connect a supported RTL2838 (`0bda:2838`) USB receiver,
restart the app, then enter your existing sharing key on its protected setup page.
Do not run two feeders with the same sharing key at the same time.

Read the verification limits below before installing it on an unattended receiver.

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
- Web assets live in `hooks/web`, which Umbrel copies during app updates. This is
  a passive asset directory, not an executable lifecycle hook. The container
  mounts it read-only, so updates do not require manual code copying.

## Verification

```bash
python3 -m unittest discover -s moritz-fr24 -p 'test_*.py'
bash -n moritz-fr24/exports.sh
```

Validated on one Raspberry Pi 4 ARM64 with a Nooelec NESDR SMArt v5: USB opens,
aircraft are tracked, FR24 connects, native key=value status is parsed and feeding
resumes after a real device reboot. A native Umbrel 2.0.1 update to 0.1.2 installed
the web assets without a manual copy. Six focused Python tests pass. This does not
prove every receiver/host combination or long-running load; verify your own
hardware and security requirements. Other Umbrel apps are independent of this package.

## Distribution

This repository contains only the app-store packages. Never commit sharing keys,
exact receiver coordinates or MCP tokens. Adding a community store is an owner
action; the current Umbrel MCP tool set has no add-repository tool.

The wrapper and package code is MIT-licensed. Upstream container images and their
included binaries retain their respective licenses; they are downloaded directly
from upstream registries, not redistributed in this repository.
