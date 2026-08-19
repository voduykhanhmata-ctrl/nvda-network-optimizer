# NVDA Network Optimizer

[English](README.md) | [Tiếng Việt](README.vi.md)

NVDA Network Optimizer is an NVDA add-on for inspecting and diagnosing network connectivity. It adapts useful ideas from `Toi_uu_mang_Nang_Cao_20_lenh.bat` without running a batch of commands that could disrupt an existing network configuration.

**Author:** Võ Duy Khánh

## Highlights

- Run a quick, read-only check of network information and DNS responsiveness.
- Test Cloudflare, Google Public DNS, and Quad9, then **suggest** the most responsive enabled IPv4 DNS service.
- Choose the network connection yourself, review its current DNS servers, and confirm before any DNS change. The report retains results from before and after the operation.
- Keep potentially disruptive operations, such as Winsock reset, proxy reset, and ARP-cache clearing, separate with clear explanations, confirmation, and a Windows administrator prompt.
- Use the **Network Optimization and Diagnostics** page in NVDA Settings to enable or disable individual task groups, choose which public DNS services are measured, and show or hide the shortcut in the Tools menu.
- Do not include firewall resets, IP release/renew operations, bulk IPv4/IPv6 resets, or TCP Chimney from the original batch file. These actions can remove a working configuration or are obsolete.
- Do not provide a free-form command field. Administrator-level actions use a fixed set of built-in Windows PowerShell operations; the add-on does not run bundled scripts with elevated privileges.

## Languages

The add-on interface, metadata, and Help are available in English and Vietnamese. English is the fallback for other NVDA interface languages.

## Building

Run `build_addon.ps1` in PowerShell from the project folder. It creates `NetworkOptimizer-1.2.0.nvda-addon`.

## Installation

Open the `.nvda-addon` file, accept the installation in NVDA, and restart NVDA if requested. The add-on targets NVDA 2026.1.

## Configuring and finding the add-on

In NVDA, open **Preferences → Settings → Network Optimization and Diagnostics**. From this page, you can:

- Enable or disable the DNS assistant and select Cloudflare, Google Public DNS, and/or Quad9 for testing and suggestions.
- Show or hide the maintenance, advanced, and stronger repair task groups to keep the interface focused on the features you need.
- Show or hide the shortcut in **Tools**. If it is hidden, you can still open this settings page through **Preferences → Settings** or assign a gesture to “Open Network Optimization and Diagnostics settings” in Input Gestures.

The add-on window also contains a **Customize add-on** button that opens this page directly.

## Important notes

DNS responsiveness is not the same as download speed. DNS profiles use IPv4 addresses; the add-on does not disable IPv6, and Windows or a VPN may still use another DNS service. Do not use stronger repair operations while connected through RDP, a VPN, or an organization-managed network unless you understand the current configuration.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or pull request. A Vietnamese guide is available in [CONTRIBUTING.vi.md](CONTRIBUTING.vi.md).

## License

This project is released under the [MIT License](LICENSE). Copyright © 2026 Võ Duy Khánh.
