# Birdhouse offline-only boundary
This assignment is static source/document analysis and sanitized report writing. The physical board is not on the execution host. Hardware activity, OS changes and test uploads are not authorized.
- Do not open or enumerate /dev, /sys USB/tty/block/I2C devices. No flashing, firmware transfer, erase, bootloader entry, reset, reconnect, mount or vendor deployment tools.
- Do not modify host driver policy, service state, permissions, power modes, boot settings or packages. No sudo or privilege elevation.
- Never start unsandboxed work, ask for an exception, invoke other agents/remote computers, modify security settings, or use indirect tools to bypass restrictions.
- Python research uses only the existing interpreter provided as BH_PYTHON. No new Python environment.
- Only write the specified new sanitized report files inside the repo, and temporary private results under permitted paths. Do not touch private serial logs or publish raw evidence.
- If any part needs active hardware I/O, mark it blocked and return to the owner with a narrowly scoped proposed next gate. Physical Flash remains NO-GO.
