# -*- coding: utf-8 -*-
"""An accessible, deliberately conservative network utility for NVDA."""

from __future__ import annotations

import addonHandler

addonHandler.initTranslation()

import base64
import config
import ctypes
import json
import locale
import os
import re
import subprocess
import threading
import time
from ctypes import wintypes

import globalPluginHandler
import gui
import scriptHandler
import ui
import wx
from gui.settingsDialogs import NVDASettingsDialog, SettingsPanel


CONFIG_SECTION = "networkOptimizer"
CONFIG_SPEC = {
	"showToolsMenu": "boolean(default=True)",
	"enableDnsAssistant": "boolean(default=True)",
	"dnsCloudflare": "boolean(default=True)",
	"dnsGoogle": "boolean(default=True)",
	"dnsQuad9": "boolean(default=True)",
	"showMaintenance": "boolean(default=True)",
	"showAdvanced": "boolean(default=False)",
	"showStrongRepair": "boolean(default=False)",
}


DNS_PROVIDERS = (
	("cloudflare", _("Cloudflare"), ("1.1.1.1", "1.0.0.1")),
	("google", _("Google Public DNS"), ("8.8.8.8", "8.8.4.4")),
	("quad9", _("Quad9"), ("9.9.9.9", "149.112.112.112")),
)


class Action:
	"""A fixed, user-explainable operation. No command text comes from the user."""

	def __init__(self, identifier, title, description, confirmation, needs_adapter=False):
		self.identifier = identifier
		self.title = title
		self.description = description
		self.confirmation = confirmation
		self.needs_adapter = needs_adapter


ACTIONS = (
	Action(
		"diagnose",
		_("Cơ bản: Kiểm tra nhanh (an toàn, không thay đổi)"),
		_("Xem kết nối đang hoạt động, cấu hình TCP/proxy và đo độ phản hồi của các DNS công cộng đã bật trong Cài đặt. Không thay đổi cài đặt."),
		"",
	),
	Action(
		"fastDns",
		_("Cơ bản: Tự chọn DNS phản hồi nhanh nhất"),
		_("Đo phản hồi của các DNS đã bật trong Cài đặt; sau đó bạn mới chọn có áp dụng DNS IPv4 được đề xuất cho một kết nối hay không."),
		_("Tiện ích sẽ đo phản hồi DNS trước. Nếu có đề xuất, việc áp dụng sẽ thay DNS IPv4 hiện tại của kết nối đã chọn và cần quyền quản trị Windows."),
		True,
	),
	Action(
		"restoreDhcpDns",
		_("Cơ bản: Khôi phục DNS tự động (DHCP)"),
		_("Bỏ DNS IPv4 đã đặt thủ công để dùng DNS do router hoặc nhà mạng cấp."),
		_("DNS IPv4 thủ công của kết nối đã chọn sẽ bị thay bằng DNS tự động từ DHCP. Windows sẽ yêu cầu quyền quản trị. Tiếp tục?"),
		True,
	),
	Action(
		"flushDns",
		_("Bảo trì: Xóa bộ nhớ đệm DNS"),
		_("Xóa các bản ghi DNS tạm trên máy. Hữu ích khi một tên miền vừa đổi địa chỉ."),
		_("Windows sẽ xóa DNS cache. Thao tác này không thay DNS đã cài, nhưng cần quyền quản trị. Tiếp tục?"),
	),
	Action(
		"clearArp",
		_("Nâng cao: Xóa ARP cache"),
		_("Buộc Windows học lại địa chỉ thiết bị trong mạng nội bộ. Kết nối LAN có thể chậm thoáng qua."),
		_("ARP cache sẽ bị xóa. Kết nối mạng nội bộ có thể chậm hoặc ngắt thoáng qua. Windows sẽ yêu cầu quyền quản trị. Tiếp tục?"),
	),
	Action(
		"tcpAutoTuningNormal",
		_("Nâng cao: Đặt TCP Auto-Tuning = Normal"),
		_("Khôi phục mức Auto-Tuning TCP Normal của Windows. Đây không phải cam kết tăng tốc Internet."),
		_("TCP Auto-Tuning sẽ được đặt thành Normal. Thao tác có thể không làm mạng nhanh hơn và cần quyền quản trị. Tiếp tục?"),
	),
	Action(
		"resetProxy",
		_("Nâng cao: Xóa proxy WinHTTP"),
		_("Đặt lại proxy cấp hệ thống dùng bởi một số dịch vụ Windows. Không dùng nếu cơ quan/trường học yêu cầu proxy."),
		_("Proxy WinHTTP hiện tại sẽ bị xóa. Một số ứng dụng cơ quan, VPN hoặc dịch vụ có thể mất kết nối. Windows sẽ yêu cầu quyền quản trị. Tiếp tục?"),
	),
	Action(
		"winsockReset",
		_("Khắc phục mạnh: Đặt lại Winsock (cần khởi động lại)"),
		_("Đặt lại thành phần mạng Windows. Chỉ dùng khi các cách cơ bản không hiệu quả; VPN hoặc phần mềm bảo mật có thể cần cấu hình lại."),
		_("Winsock sẽ được đặt lại. VPN, proxy hoặc phần mềm bảo mật có thể bị ảnh hưởng và bạn cần khởi động lại Windows. Windows sẽ yêu cầu quyền quản trị. Tiếp tục?"),
	),
)

ACTION_BY_ID = {action.identifier: action for action in ACTIONS}
PROVIDER_BY_ID = {identifier: (name, servers) for identifier, name, servers in DNS_PROVIDERS}
PROVIDER_SETTING_BY_ID = {
	"cloudflare": "dnsCloudflare",
	"google": "dnsGoogle",
	"quad9": "dnsQuad9",
}

# Fixed probe: it uses Windows' DNS client cmdlet rather than ICMP ping, which is
# a more meaningful signal for choosing a DNS resolver. It never receives user input.
DNS_BENCHMARK_COMMAND_TEMPLATE = r"""
$ErrorActionPreference = 'Stop'
$servers = @(__SERVERS__)
$results = foreach ($server in $servers) {
	$samples = @()
	foreach ($attempt in 1..3) {
		$timer = [System.Diagnostics.Stopwatch]::StartNew()
		try {
			Resolve-DnsName -Name 'www.example.com' -Type A -Server $server -DnsOnly -NoHostsFile -QuickTimeout -ErrorAction Stop | Out-Null
			$timer.Stop()
			$samples += [math]::Round($timer.Elapsed.TotalMilliseconds)
		} catch {
			$timer.Stop()
		}
	}
	$ordered = @($samples | Sort-Object)
	[pscustomobject]@{
		Server = $server
		Successes = $ordered.Count
		MedianMilliseconds = if ($ordered.Count) {
			[math]::Round($ordered[[int][math]::Floor(($ordered.Count - 1) / 2)])
		} else { $null }
	}
}
$results | ConvertTo-Json -Compress
"""

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_NOASYNC = 0x00000100
SW_HIDE = 0
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
ELEVATED_ACTION_TIMEOUT_MS = 120000
COINIT_APARTMENTTHREADED = 0x2
COINIT_DISABLE_OLE1DDE = 0x4


class _ShellExecuteInfo(ctypes.Structure):
	_fields_ = (
		("cbSize", wintypes.DWORD),
		("fMask", wintypes.ULONG),
		("hwnd", wintypes.HWND),
		("lpVerb", wintypes.LPCWSTR),
		("lpFile", wintypes.LPCWSTR),
		("lpParameters", wintypes.LPCWSTR),
		("lpDirectory", wintypes.LPCWSTR),
		("nShow", ctypes.c_int),
		("hInstApp", wintypes.HINSTANCE),
		("lpIDList", ctypes.c_void_p),
		("lpClass", wintypes.LPCWSTR),
		("hkeyClass", wintypes.HKEY),
		("dwHotKey", wintypes.DWORD),
		("hIconOrMonitor", wintypes.HANDLE),
		("hProcess", wintypes.HANDLE),
	)


def _run_process(argv, timeout=20):
	"""Run a fixed command off the GUI thread and return its visible output."""
	creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
	encoding = locale.getpreferredencoding(False) or "utf-8"
	try:
		process = subprocess.Popen(
			argv,
			stdin=subprocess.DEVNULL,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			shell=False,
			creationflags=creation_flags,
			encoding=encoding,
			errors="replace",
		)
		output, _unused = process.communicate(timeout=timeout)
		return process.returncode, (output or "").strip()
	except subprocess.TimeoutExpired:
		process.kill()
		output, _unused = process.communicate()
		return -1, _("Hết thời gian chờ. ") + (output or "").strip()
	except OSError as error:
		return -1, str(error)


def _active_adapters(require_verified=False):
	"""Read connected IPv4 interfaces with a static PowerShell expression."""
	command = (
		"@(" 
		"Get-NetIPConfiguration | Where-Object {$_.IPv4Address} | ForEach-Object { "
		"[pscustomobject]@{ "
		"InterfaceIndex=$_.InterfaceIndex; "
		"InterfaceAlias=$_.InterfaceAlias; "
		"IPv4=@($_.IPv4Address | ForEach-Object {$_.IPAddress}) -join ', '; "
		"Gateway=@($_.IPv4DefaultGateway | ForEach-Object {$_.NextHop}) -join ', '; "
		"Dns=@($_.DNSServer.ServerAddresses) -join ', '; "
		"HasDefaultRoute=[bool]$_.IPv4DefaultGateway "
		"} "
		"} "
		") | ConvertTo-Json -Compress"
	)
	code, output = _run_process(
		["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
		timeout=12,
	)
	if code != 0:
		return [] if require_verified else _active_adapters_from_netsh()
	try:
		data = json.loads(output) if output else []
	except ValueError:
		return [] if require_verified else _active_adapters_from_netsh()
	if isinstance(data, dict):
		data = [data]
	interfaces = []
	for item in data if isinstance(data, list) else []:
		try:
			index = int(item.get("InterfaceIndex", 0))
		except (TypeError, ValueError):
			continue
		alias = str(item.get("InterfaceAlias") or "").strip()
		if index > 0 and alias:
			interfaces.append(
				{
					"index": index,
					"alias": alias,
					"ipv4": str(item.get("IPv4") or "").strip(),
					"gateway": str(item.get("Gateway") or "").strip(),
					"dns": str(item.get("Dns") or "").strip(),
					"has_default_route": bool(item.get("HasDefaultRoute")),
				}
			)
	# Interfaces with a default route are normally the ones novices expect to change.
	if require_verified:
		interfaces = [interface for interface in interfaces if interface["has_default_route"]]
	if not interfaces:
		return [] if require_verified else _active_adapters_from_netsh()
	return sorted(interfaces, key=lambda interface: (not interface["has_default_route"], interface["alias"].lower()))


def _active_adapters_from_netsh():
	"""Fallback for systems where the NetTCPIP CIM provider is unavailable."""
	code, output = _run_process(["netsh.exe", "interface", "ipv4", "show", "interfaces"], timeout=12)
	if code != 0:
		return []
	interfaces = []
	for line in output.splitlines():
		# The final two fields are State and Name; the first three fields are numeric.
		match = re.match(r"^\s*(\d+)\s+\d+\s+\d+\s+(\S+)\s+(.+?)\s*$", line)
		if not match:
			continue
		index = int(match.group(1))
		state = match.group(2).lower()
		alias = match.group(3).strip()
		if "loopback" in alias.lower() or state in ("disconnected", "disabled"):
			continue
		_dns_code, dns_output = _run_process(
			["netsh.exe", "interface", "ipv4", "show", "dnsservers", "name={}".format(index)],
			timeout=8,
		)
		dns_servers = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", dns_output)
		interfaces.append(
			{
				"index": index,
				"alias": alias,
				"ipv4": "",
				"gateway": "",
				"dns": ", ".join(dict.fromkeys(dns_servers)),
				"has_default_route": False,
			}
		)
	return interfaces


def _adapter_label(adapter):
	parts = [adapter["alias"], _("IPv4: ") + (adapter["ipv4"] or _("không rõ"))]
	if adapter["dns"]:
		parts.append(_("DNS hiện tại: ") + adapter["dns"])
	return " — ".join(parts)


def _configured_dns_providers():
	"""Return only built-in DNS profiles explicitly enabled in NVDA Settings."""
	settings = config.conf[CONFIG_SECTION]
	if not settings["enableDnsAssistant"]:
		return ()
	return tuple(
		provider
		for provider in DNS_PROVIDERS
		if settings[PROVIDER_SETTING_BY_ID[provider[0]]]
	)


def _dns_benchmark_command(providers):
	"""Build a probe from fixed built-in IP addresses; it accepts no user text."""
	servers = ", ".join("'{}'".format(provider[2][0]) for provider in providers)
	if not servers:
		raise ValueError("Không có DNS nào được chọn để đo.")
	return DNS_BENCHMARK_COMMAND_TEMPLATE.replace("__SERVERS__", servers)


def _measure_dns_providers(providers):
	"""Measure selected fixed resolvers in one background PowerShell process."""
	if not providers:
		return []
	code, output = _run_process(
		["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _dns_benchmark_command(providers)],
		timeout=35,
	)
	measurements = {}
	if code == 0:
		try:
			data = json.loads(output)
			if isinstance(data, dict):
				data = [data]
			for item in data if isinstance(data, list) else []:
				server = str(item.get("Server") or "")
				latency = item.get("MedianMilliseconds")
				successes = int(item.get("Successes") or 0)
				measurements[server] = (int(latency) if latency is not None else None, successes)
		except (TypeError, ValueError):
			pass
	return [
		(identifier, name, servers, *measurements.get(servers[0], (None, 0)))
		for identifier, name, servers in providers
	]


def _trim_output(output, limit=2500):
	if len(output) <= limit:
		return output
	return output[:limit] + "\n" + _("… (đã rút gọn)")


def _elevated_script_for_action(action_id, provider_id=None, adapter=None):
	"""Return a fixed PowerShell program for one allow-listed administrative task.

	Only a parsed integer interface index and one of the three built-in DNS profiles
	may enter the program. No user-supplied command, path, adapter name, or text is
	executed with elevation.
	"""
	prefix = "$ErrorActionPreference = 'Stop'\ntry {\n"
	suffix = "\n\texit 0\n} catch {\n\tWrite-Error $_\n\texit 1\n}"
	if action_id == "applyDns":
		if provider_id not in PROVIDER_BY_ID or not adapter:
			raise ValueError("Thiếu thông tin DNS hoặc kết nối mạng.")
		interface_index = int(adapter["index"])
		if interface_index <= 0:
			raise ValueError("Chỉ số kết nối mạng không hợp lệ.")
		_provider_name, servers = PROVIDER_BY_ID[provider_id]
		body = """
	$config = Get-NetIPConfiguration -InterfaceIndex {index} -ErrorAction Stop
	if (-not $config.IPv4Address) {{ throw 'Kết nối không có địa chỉ IPv4.' }}
	if (-not $config.IPv4DefaultGateway) {{ throw 'Kết nối không có cổng mặc định; có thể là VPN hoặc kết nối ảo.' }}
	Set-DnsClientServerAddress -InterfaceIndex {index} -ServerAddresses @('{primary}', '{secondary}') -Validate -ErrorAction Stop
	""".format(index=interface_index, primary=servers[0], secondary=servers[1])
	elif action_id == "restoreDhcpDns":
		if not adapter:
			raise ValueError("Thiếu thông tin kết nối mạng.")
		interface_index = int(adapter["index"])
		if interface_index <= 0:
			raise ValueError("Chỉ số kết nối mạng không hợp lệ.")
		body = """
	$config = Get-NetIPConfiguration -InterfaceIndex {index} -ErrorAction Stop
	if (-not $config.IPv4Address) {{ throw 'Kết nối không có địa chỉ IPv4.' }}
	if (-not $config.IPv4DefaultGateway) {{ throw 'Kết nối không có cổng mặc định; có thể là VPN hoặc kết nối ảo.' }}
	Set-DnsClientServerAddress -InterfaceIndex {index} -ResetServerAddresses -ErrorAction Stop
	""".format(index=interface_index)
	elif action_id == "flushDns":
		body = "Clear-DnsClientCache -ErrorAction Stop"
	elif action_id == "clearArp":
		body = """
	& (Join-Path $env:SystemRoot 'System32\\arp.exe') -d '*'
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	"""
	elif action_id == "winsockReset":
		body = """
	& (Join-Path $env:SystemRoot 'System32\\netsh.exe') winsock reset
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	"""
	elif action_id == "resetProxy":
		body = """
	& (Join-Path $env:SystemRoot 'System32\\netsh.exe') winhttp reset proxy
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	"""
	elif action_id == "tcpAutoTuningNormal":
		body = """
	& (Join-Path $env:SystemRoot 'System32\\netsh.exe') interface tcp set global autotuninglevel=normal
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	"""
	else:
		raise ValueError("Tác vụ quản trị không hợp lệ.")
	return prefix + body + suffix


def _run_elevated_powershell(script):
	"""Run in-memory fixed code under UAC and return (exit_code, launch_error)."""
	encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
	parameters = subprocess.list2cmdline(("-NoProfile", "-NonInteractive", "-EncodedCommand", encoded))
	info = _ShellExecuteInfo()
	info.cbSize = ctypes.sizeof(_ShellExecuteInfo)
	info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
	info.hwnd = getattr(gui.mainFrame, "Handle", None)
	info.lpVerb = "runas"
	powershell_path = os.path.join(
		os.environ.get("SystemRoot", r"C:\Windows"),
		"System32",
		"WindowsPowerShell",
		"v1.0",
		"powershell.exe",
	)
	info.lpFile = powershell_path
	info.lpParameters = parameters
	info.lpDirectory = os.environ.get("SystemRoot")
	info.nShow = SW_HIDE

	shell32 = ctypes.WinDLL("shell32", use_last_error=True)
	kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
	shell_execute_ex = shell32.ShellExecuteExW
	shell_execute_ex.argtypes = (ctypes.POINTER(_ShellExecuteInfo),)
	shell_execute_ex.restype = wintypes.BOOL
	kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
	kernel32.WaitForSingleObject.restype = wintypes.DWORD
	kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
	kernel32.GetExitCodeProcess.restype = wintypes.BOOL
	kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
	kernel32.CloseHandle.restype = wintypes.BOOL
	ole32 = ctypes.WinDLL("ole32", use_last_error=True)
	ole32.CoInitializeEx.argtypes = (ctypes.c_void_p, wintypes.DWORD)
	ole32.CoInitializeEx.restype = ctypes.c_long
	ole32.CoUninitialize.argtypes = ()
	ole32.CoUninitialize.restype = None
	com_result = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE)
	com_initialized = com_result >= 0
	try:
		if not shell_execute_ex(ctypes.byref(info)):
			return None, ctypes.get_last_error()
		if not info.hProcess:
			return None, 0
		wait_result = kernel32.WaitForSingleObject(info.hProcess, ELEVATED_ACTION_TIMEOUT_MS)
		if wait_result == WAIT_TIMEOUT:
			return None, "timeout"
		if wait_result != WAIT_OBJECT_0:
			return None, ctypes.get_last_error()
		exit_code = wintypes.DWORD()
		if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
			return None, ctypes.get_last_error()
		return int(exit_code.value), None
	finally:
		if info.hProcess:
			kernel32.CloseHandle(info.hProcess)
		if com_initialized:
			ole32.CoUninitialize()


def _post_action_report(action_id, provider_id, adapter, exit_code, launch_error):
	if launch_error == 1223:
		return _("Đã hủy yêu cầu quyền quản trị. Tác vụ chưa được chạy."), False
	if launch_error == "timeout":
		return _("Tác vụ vẫn chưa kết thúc sau 2 phút. Không chạy lại ngay; hãy kiểm tra trạng thái mạng trước."), False
	if launch_error is not None:
		return _("Windows không thể khởi chạy tác vụ có quyền quản trị (mã {}).").format(launch_error), False
	if exit_code != 0:
		return _("Windows báo tác vụ không hoàn tất (mã {}). Không thay đổi thêm và hãy kiểm tra lại cấu hình mạng.").format(exit_code), False

	if action_id == "applyDns":
		provider_name, servers = PROVIDER_BY_ID[provider_id]
		_code, output = _run_process(
			["netsh.exe", "interface", "ipv4", "show", "dnsservers", "name={}".format(adapter["index"])],
			timeout=12,
		)
		return "\n".join((
			_("KẾT QUẢ ÁP DỤNG DNS"),
			_("Đã yêu cầu đặt {}: {} và {} cho kết nối '{}'.").format(provider_name, servers[0], servers[1], adapter["alias"]),
			"",
			_("Cấu hình đọc lại:"),
			_trim_output(output),
		)), True
	if action_id == "restoreDhcpDns":
		_code, output = _run_process(
			["netsh.exe", "interface", "ipv4", "show", "dnsservers", "name={}".format(adapter["index"])],
			timeout=12,
		)
		return "\n".join((
			_("Đã yêu cầu khôi phục DNS tự động (DHCP) cho '{}'.").format(adapter["alias"]),
			"",
			_("Cấu hình đọc lại:"),
			_trim_output(output),
		)), True
	if action_id == "winsockReset":
		return _("Đã đặt lại Winsock. Hãy khởi động lại Windows trước khi đánh giá kết quả."), True
	if action_id == "resetProxy":
		return _("Đã đặt lại proxy WinHTTP."), True
	if action_id == "tcpAutoTuningNormal":
		return _("Đã đặt TCP Auto-Tuning = Normal."), True
	if action_id == "clearArp":
		return _("Đã xóa ARP cache."), True
	return _("Đã xóa bộ nhớ đệm DNS của Windows."), True


class NetworkOptimizerSettingsPanel(SettingsPanel):
	"""Preferences intentionally control visibility, never run a network action."""

	title = _("Tối ưu và chẩn đoán mạng")
	_plugin = None

	def makeSettings(self, settingsSizer):
		intro = wx.StaticText(
			self,
			label=_(
				"Chọn các chức năng muốn hiển thị. Việc đổi DNS hoặc thay đổi mạng vẫn luôn cần "
				"xác nhận riêng và quyền quản trị Windows."
			),
		)
		intro.Wrap(650)
		settingsSizer.Add(intro, 0, wx.ALL | wx.EXPAND, 10)

		self._show_tools_menu = self._add_checkbox(
			settingsSizer,
			_("Hiển thị lối tắt mở add-on trong menu &Công cụ của NVDA"),
			"showToolsMenu",
		)

		settingsSizer.Add(wx.StaticText(self, label=_("Trợ lý DNS")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
		self._enable_dns_assistant = self._add_checkbox(
			settingsSizer,
			_("Bật trợ lý &DNS: đo, đề xuất, đổi và khôi phục DNS IPv4"),
			"enableDnsAssistant",
		)
		self._dns_cloudflare = self._add_checkbox(
			settingsSizer,
			_("Đo và cho phép dùng &Cloudflare (1.1.1.1)"),
			"dnsCloudflare",
		)
		self._dns_google = self._add_checkbox(
			settingsSizer,
			_("Đo và cho phép dùng &Google Public DNS (8.8.8.8)"),
			"dnsGoogle",
		)
		self._dns_quad9 = self._add_checkbox(
			settingsSizer,
			_("Đo và cho phép dùng &Quad9 (9.9.9.9, có lọc bảo mật)"),
			"dnsQuad9",
		)

		settingsSizer.Add(wx.StaticText(self, label=_("Các nhóm tác vụ")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
		self._show_maintenance = self._add_checkbox(
			settingsSizer,
			_("Hiển thị &bảo trì: Xóa bộ nhớ đệm DNS"),
			"showMaintenance",
		)
		self._show_advanced = self._add_checkbox(
			settingsSizer,
			_("Hiển thị tác vụ &nâng cao: ARP cache, TCP Auto-Tuning và proxy"),
			"showAdvanced",
		)
		self._show_strong_repair = self._add_checkbox(
			settingsSizer,
			_("Hiển thị khắc phục &mạnh: Đặt lại Winsock (cần khởi động lại)"),
			"showStrongRepair",
		)

		self._dns_controls = (self._dns_cloudflare, self._dns_google, self._dns_quad9)
		self._enable_dns_assistant.Bind(wx.EVT_CHECKBOX, self._on_dns_assistant_changed)
		self._update_dns_controls()

	def _add_checkbox(self, sizer, label, key):
		checkbox = wx.CheckBox(self, label=label)
		checkbox.SetValue(bool(config.conf[CONFIG_SECTION][key]))
		sizer.Add(checkbox, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 10)
		return checkbox

	def _on_dns_assistant_changed(self, _event):
		self._update_dns_controls()

	def _update_dns_controls(self):
		enabled = self._enable_dns_assistant.IsChecked()
		for control in self._dns_controls:
			control.Enable(enabled)

	def isValid(self):
		if self._enable_dns_assistant.IsChecked() and not any(control.IsChecked() for control in self._dns_controls):
			wx.MessageBox(
				_("Hãy chọn ít nhất một nhà cung cấp DNS, hoặc bỏ chọn Trợ lý DNS."),
				self.title,
				wx.OK | wx.ICON_WARNING,
				self,
			)
			self._dns_cloudflare.SetFocus()
			return False
		return True

	def onSave(self):
		settings = config.conf[CONFIG_SECTION]
		settings["showToolsMenu"] = self._show_tools_menu.IsChecked()
		settings["enableDnsAssistant"] = self._enable_dns_assistant.IsChecked()
		settings["dnsCloudflare"] = self._dns_cloudflare.IsChecked()
		settings["dnsGoogle"] = self._dns_google.IsChecked()
		settings["dnsQuad9"] = self._dns_quad9.IsChecked()
		settings["showMaintenance"] = self._show_maintenance.IsChecked()
		settings["showAdvanced"] = self._show_advanced.IsChecked()
		settings["showStrongRepair"] = self._show_strong_repair.IsChecked()
		plugin = type(self)._plugin
		if plugin:
			plugin.apply_preferences()


class NetworkOptimizerDialog(wx.Dialog):
	def __init__(self, parent, plugin, actions):
		super().__init__(parent, title=_("Tối ưu và chẩn đoán mạng"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self._plugin = plugin
		self._actions = tuple(actions)

		outer = wx.BoxSizer(wx.VERTICAL)
		intro = wx.StaticText(
			self,
			label=_("Chọn một tác vụ. Tác vụ Cơ bản là an toàn; các tác vụ khác luôn giải thích tác động và yêu cầu xác nhận trước khi thay đổi mạng."),
		)
		intro.Wrap(620)
		outer.Add(intro, 0, wx.ALL | wx.EXPAND, 10)

		self._choice = wx.Choice(self, choices=[action.title for action in self._actions])
		if self._actions:
			self._choice.SetSelection(0)
		outer.Add(wx.StaticText(self, label=_("Tác vụ:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
		outer.Add(self._choice, 0, wx.ALL | wx.EXPAND, 10)

		self._description = wx.StaticText(self, label="")
		self._description.Wrap(620)
		outer.Add(self._description, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

		self._status = wx.StaticText(self, label=_("Sẵn sàng."))
		outer.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

		outer.Add(wx.StaticText(self, label=_("Kết quả:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
		self._result = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
		self._result.SetMinSize((640, 260))
		outer.Add(self._result, 1, wx.ALL | wx.EXPAND, 10)

		buttons = wx.BoxSizer(wx.HORIZONTAL)
		self._run_button = wx.Button(self, label=_("&Chạy tác vụ"))
		self._copy_button = wx.Button(self, label=_("&Sao chép kết quả"))
		self._addon_settings_button = wx.Button(self, label=_("&Tùy chỉnh add-on"))
		self._settings_button = wx.Button(self, label=_("Mở cài đặt &mạng Windows"))
		self._close_button = wx.Button(self, wx.ID_CLOSE, label=_("Đó&ng"))
		for button in (self._run_button, self._copy_button, self._addon_settings_button, self._settings_button, self._close_button):
			buttons.Add(button, 0, wx.ALL, 5)
		outer.Add(buttons, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

		self.SetSizerAndFit(outer)
		self.SetMinSize((680, 520))
		self.CentreOnScreen()

		self._choice.Bind(wx.EVT_CHOICE, self._on_choice)
		self._run_button.Bind(wx.EVT_BUTTON, self._on_run)
		self._copy_button.Bind(wx.EVT_BUTTON, self._on_copy)
		self._addon_settings_button.Bind(wx.EVT_BUTTON, self._on_addon_settings)
		self._settings_button.Bind(wx.EVT_BUTTON, self._on_settings)
		self._close_button.Bind(wx.EVT_BUTTON, self._on_close)
		self.Bind(wx.EVT_CLOSE, self._on_close)
		self._refresh_action_description()

	def selected_action(self):
		selection = self._choice.GetSelection()
		if 0 <= selection < len(self._actions):
			return self._actions[selection]
		return None

	def refresh_actions(self, actions):
		current = self.selected_action()
		current_id = current.identifier if current else None
		self._actions = tuple(actions)
		self._choice.Clear()
		for action in self._actions:
			self._choice.Append(action.title)
		if self._actions:
			selection = next(
				(index for index, action in enumerate(self._actions) if action.identifier == current_id),
				0,
			)
			self._choice.SetSelection(selection)
		self._run_button.Enable(bool(self._actions))
		self._refresh_action_description()

	def set_busy(self, busy, status=None):
		self._choice.Enable(not busy and bool(self._actions))
		self._run_button.Enable(not busy and bool(self._actions))
		self._addon_settings_button.Enable(not busy)
		self._settings_button.Enable(not busy)
		if status:
			self._status.SetLabel(status)

	def show_result(self, text, status=None):
		self._result.SetValue(text)
		if status:
			self._status.SetLabel(status)

	def append_result(self, text, status=None):
		previous = self._result.GetValue().rstrip()
		self._result.SetValue((previous + "\n\n" if previous else "") + text)
		if status:
			self._status.SetLabel(status)

	def _refresh_action_description(self):
		action = self.selected_action()
		self._description.SetLabel(action.description if action else _("Không có tác vụ nào đang được hiển thị."))
		self._description.Wrap(620)
		self.Layout()

	def _on_choice(self, _event):
		self._refresh_action_description()

	def _on_run(self, _event):
		action = self.selected_action()
		if action:
			self._plugin.run_action(action)

	def _on_copy(self, _event):
		text = self._result.GetValue()
		if not text:
			ui.message(_("Chưa có kết quả để sao chép."))
			return
		if wx.TheClipboard.Open():
			try:
				wx.TheClipboard.SetData(wx.TextDataObject(text))
			finally:
				wx.TheClipboard.Close()
			ui.message(_("Đã sao chép kết quả."))
		else:
			ui.message(_("Không thể mở bảng nhớ tạm."))

	def _on_addon_settings(self, _event):
		self._plugin.open_addon_settings()

	def _on_settings(self, _event):
		try:
			os.startfile("ms-settings:network-status")
		except OSError:
			ui.message(_("Không thể mở cài đặt mạng Windows."))

	def _on_close(self, _event):
		self._plugin.dialog_closed(self)
		self.Destroy()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		# Register the schema before either the Settings panel or action filter reads it.
		config.conf.spec[CONFIG_SECTION] = CONFIG_SPEC
		NetworkOptimizerSettingsPanel._plugin = self
		if NetworkOptimizerSettingsPanel not in NVDASettingsDialog.categoryClasses:
			NVDASettingsDialog.categoryClasses.append(NetworkOptimizerSettingsPanel)
		self._dialog = None
		self._terminated = False
		self._tools_menu = gui.mainFrame.sysTrayIcon.toolsMenu
		self._menu_item = None
		self.apply_preferences()

	def terminate(self):
		self._terminated = True
		if self._dialog:
			try:
				self._dialog.Destroy()
			except RuntimeError:
				pass
			self._dialog = None
		self._remove_tools_menu_item()
		try:
			NVDASettingsDialog.categoryClasses.remove(NetworkOptimizerSettingsPanel)
		except ValueError:
			pass
		NetworkOptimizerSettingsPanel._plugin = None
		super().terminate()

	def _install_tools_menu_item(self):
		if self._menu_item is not None:
			return
		self._menu_item = self._tools_menu.Append(wx.ID_ANY, _("&Tối ưu và chẩn đoán mạng..."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu, self._menu_item)

	def _remove_tools_menu_item(self):
		menu_item = self._menu_item
		if menu_item is None:
			return
		self._menu_item = None
		try:
			gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, handler=self._on_menu, id=menu_item.GetId())
			self._tools_menu.Remove(menu_item)
			menu_item.Destroy()
		except (AttributeError, RuntimeError):
			pass

	def _available_actions(self):
		"""Filter the fixed allow-list into a small, beginner-friendly action list."""
		settings = config.conf[CONFIG_SECTION]
		action_ids = ["diagnose"]
		if settings["enableDnsAssistant"]:
			action_ids.extend(("fastDns", "restoreDhcpDns"))
		if settings["showMaintenance"]:
			action_ids.append("flushDns")
		if settings["showAdvanced"]:
			action_ids.extend(("clearArp", "tcpAutoTuningNormal", "resetProxy"))
		if settings["showStrongRepair"]:
			action_ids.append("winsockReset")
		return tuple(ACTION_BY_ID[action_id] for action_id in action_ids)

	def apply_preferences(self):
		"""Reflect stored preferences immediately without performing any network change."""
		if config.conf[CONFIG_SECTION]["showToolsMenu"]:
			self._install_tools_menu_item()
		else:
			self._remove_tools_menu_item()
		dialog = self._active_dialog()
		if dialog:
			dialog.refresh_actions(self._available_actions())

	def open_addon_settings(self):
		if self._terminated:
			return
		gui.mainFrame.popupSettingsDialog(NVDASettingsDialog, NetworkOptimizerSettingsPanel)

	def _on_menu(self, _event):
		if self._dialog:
			try:
				self._dialog.Raise()
				self._dialog.SetFocus()
				return
			except RuntimeError:
				self._dialog = None
		gui.mainFrame.prePopup()
		try:
			self._dialog = NetworkOptimizerDialog(gui.mainFrame, self, self._available_actions())
			self._dialog.Show()
		finally:
			gui.mainFrame.postPopup()

	@scriptHandler.script(
		description=_("Mở Tối ưu và chẩn đoán mạng"),
		category=_("Tối ưu và chẩn đoán mạng"),
	)
	def script_openNetworkOptimizer(self, gesture):
		"""Exposed in NVDA Input Gestures so users may choose their own shortcut."""
		self._on_menu(None)

	@scriptHandler.script(
		description=_("Mở phần cài đặt Tối ưu và chẩn đoán mạng"),
		category=_("Tối ưu và chẩn đoán mạng"),
	)
	def script_openNetworkOptimizerSettings(self, gesture):
		"""Exposed in NVDA Input Gestures for a direct Settings shortcut."""
		self.open_addon_settings()

	def dialog_closed(self, dialog):
		if self._dialog is dialog:
			self._dialog = None

	def run_action(self, action):
		if not action or action.identifier not in {item.identifier for item in self._available_actions()}:
			ui.message(_("Tác vụ này đang bị ẩn trong phần cài đặt add-on."))
			return
		if action.identifier == "diagnose":
			self._start_diagnostics()
		elif action.identifier == "fastDns":
			self._start_fast_dns()
		elif action.needs_adapter:
			self._choose_adapter_then_confirm(action.identifier)
		else:
			self._confirm_and_start(action.identifier)

	def _active_dialog(self):
		return self._dialog if self._dialog and self._dialog.IsShown() else None

	def _set_busy(self, busy, status=None):
		dialog = self._active_dialog()
		if dialog:
			dialog.set_busy(busy, status)

	def _start_diagnostics(self):
		providers = _configured_dns_providers()
		self._set_busy(True, _("Đang kiểm tra kết nối. Vui lòng chờ..."))
		ui.message(_("Đang kiểm tra mạng."))
		threading.Thread(target=self._diagnostics_worker, args=(providers,), daemon=True).start()

	def _diagnostics_worker(self, providers):
		adapters = _active_adapters()
		interface_code, interfaces = _run_process(["netsh.exe", "interface", "show", "interface"], timeout=12)
		tcp_code, tcp = _run_process(["netsh.exe", "interface", "tcp", "show", "global"], timeout=12)
		proxy_code, proxy = _run_process(["netsh.exe", "winhttp", "show", "proxy"], timeout=12)
		dns_results = _measure_dns_providers(providers)

		lines = [_("BÁO CÁO KIỂM TRA NHANH"), ""]
		if adapters:
			lines.append(_("Kết nối IPv4 đang hoạt động:"))
			for adapter in adapters:
				lines.append("- " + _adapter_label(adapter))
		else:
			lines.append(_("Kết nối đang hoạt động: Không xác định được."))
		lines.append("")
		if dns_results:
			lines.append(_("Phản hồi DNS (chỉ là độ phản hồi của máy chủ DNS, không phải toàn bộ tốc độ Internet):"))
			for _identifier, name, _servers, latency, successes in dns_results:
				if latency is None:
					lines.append("- {}: {}".format(name, _("không phản hồi (0/3)")))
				else:
					lines.append("- {}: {} ({}/3)".format(name, _("{} ms").format(latency), successes))
		else:
			lines.append(_("Đo DNS: Đã tắt trong phần cài đặt add-on."))
		lines.extend(("", _("Trạng thái giao diện:"), _trim_output(interfaces) if interface_code == 0 else _("Không đọc được: ") + interfaces))
		lines.extend(("", _("TCP toàn cục:"), _trim_output(tcp) if tcp_code == 0 else _("Không đọc được: ") + tcp))
		lines.extend(("", _("Proxy WinHTTP:"), _trim_output(proxy) if proxy_code == 0 else _("Không đọc được: ") + proxy))
		wx.CallAfter(self._complete_diagnostics, "\n".join(lines))

	def _complete_diagnostics(self, report):
		if self._terminated:
			return
		self._set_busy(False, _("Đã hoàn tất kiểm tra."))
		dialog = self._active_dialog()
		if dialog:
			dialog.show_result(report, _("Đã hoàn tất kiểm tra."))
		ui.message(_("Đã hoàn tất kiểm tra mạng."))

	def _start_fast_dns(self):
		providers = _configured_dns_providers()
		if not providers:
			ui.message(_("Trợ lý DNS đang tắt hoặc chưa chọn nhà cung cấp DNS. Mở phần cài đặt add-on để bật lại."))
			return
		self._set_busy(True, _("Đang đo phản hồi DNS. Vui lòng chờ..."))
		ui.message(_("Đang đo phản hồi DNS."))
		threading.Thread(target=self._fast_dns_worker, args=(providers,), daemon=True).start()

	def _fast_dns_worker(self, providers):
		results = _measure_dns_providers(providers)
		wx.CallAfter(self._complete_fast_dns, results)

	def _complete_fast_dns(self, results):
		if self._terminated:
			return
		lines = [_("KẾT QUẢ ĐO DNS"), ""]
		available = []
		for identifier, name, servers, latency, successes in results:
			if latency is None:
				lines.append("- {}: {}".format(name, _("không phản hồi (0/3)")))
			else:
				lines.append("- {} ({}): {} ({}/3)".format(name, servers[0], _("{} ms").format(latency), successes))
				available.append((successes, latency, identifier, name, servers))
		dialog = self._active_dialog()
		if not available:
			self._set_busy(False, _("Không có DNS nào phản hồi."))
			if dialog:
				dialog.show_result("\n".join(lines), _("Không có DNS nào phản hồi."))
			ui.message(_("Không có DNS công cộng nào phản hồi."))
			return

		# Prefer a stable resolver first, then the lower median response time.
		available.sort(key=lambda item: (-item[0], item[1]))
		_successes, _latency, provider_id, provider_name, servers = available[0]
		lines.extend(("", _("Đề xuất: {} ({} và {}).").format(provider_name, servers[0], servers[1]), _("Bạn vẫn cần chọn kết nối và xác nhận trước khi DNS được thay đổi.")))
		if provider_id not in {provider[0] for provider in _configured_dns_providers()}:
			status = _("Trợ lý DNS đã được tắt trong khi đang đo.")
			self._set_busy(False, status)
			if dialog:
				dialog.show_result("\n".join(lines), status)
			ui.message(status)
			return
		if dialog:
			dialog.show_result("\n".join(lines), _("Đã có đề xuất DNS."))
		ui.message(_("Đã tìm được DNS đề xuất."))
		self._choose_adapter_then_confirm("applyDns", provider_id)

	def _choose_adapter_then_confirm(self, action_id, provider_id=None):
		self._set_busy(True, _("Đang tìm kết nối đang hoạt động..."))
		threading.Thread(target=self._adapter_worker, args=(action_id, provider_id), daemon=True).start()

	def _adapter_worker(self, action_id, provider_id):
		wx.CallAfter(self._finish_choose_adapter, action_id, provider_id, _active_adapters(require_verified=True))

	def _finish_choose_adapter(self, action_id, provider_id, adapters):
		if self._terminated:
			return
		self._set_busy(False, _("Sẵn sàng."))
		if not adapters:
			ui.message(_("Không tìm thấy kết nối mạng đang hoạt động."))
			return
		adapter = adapters[0]
		if len(adapters) > 1:
			labels = [_adapter_label(item) for item in adapters]
			chooser = wx.SingleChoiceDialog(
				self._active_dialog() or gui.mainFrame,
				_("Chọn kết nối sẽ nhận cấu hình DNS IPv4. Không chọn VPN nếu bạn không chắc chắn."),
				_("Chọn kết nối mạng"),
				labels,
			)
			gui.mainFrame.prePopup()
			try:
				if chooser.ShowModal() != wx.ID_OK:
					return
				adapter = adapters[chooser.GetSelection()]
			finally:
				chooser.Destroy()
				gui.mainFrame.postPopup()
		self._confirm_and_start(action_id, provider_id=provider_id, adapter=adapter)

	def _confirm_and_start(self, action_id, provider_id=None, adapter=None):
		available_ids = {action.identifier for action in self._available_actions()}
		if action_id == "applyDns":
			if "fastDns" not in available_ids or provider_id not in {provider[0] for provider in _configured_dns_providers()}:
				ui.message(_("Trợ lý DNS đang bị tắt trong phần cài đặt add-on."))
				return
		elif action_id not in available_ids:
			ui.message(_("Tác vụ này đang bị ẩn trong phần cài đặt add-on."))
			return
		action = ACTION_BY_ID.get(action_id)
		if action_id == "applyDns":
			action = ACTION_BY_ID["fastDns"]
		if not action:
			return
		message = action.confirmation
		if action_id == "applyDns":
			provider_name, servers = PROVIDER_BY_ID[provider_id]
			provider_note = ""
			if provider_id == "quad9":
				provider_note = _(" Quad9 có bộ lọc bảo mật và có thể chặn một số tên miền.")
			message = _(
				"DNS IPv4 của kết nối '{adapter}' sẽ được thay bằng {provider}: {primary} và {secondary}. "
				"DNS hiện tại: {currentDns}. "
				"Điều này không bảo đảm Internet nhanh hơn.{providerNote} Windows sẽ yêu cầu quyền quản trị. Tiếp tục?"
			).format(adapter=adapter["alias"], provider=provider_name, primary=servers[0], secondary=servers[1], currentDns=adapter["dns"] or _("không xác định"), providerNote=provider_note)
		elif action_id == "restoreDhcpDns":
			message = _("DNS IPv4 thủ công của kết nối '{adapter}' sẽ bị thay bằng DNS tự động từ DHCP. DNS hiện tại: {currentDns}. Windows sẽ yêu cầu quyền quản trị. Tiếp tục?").format(adapter=adapter["alias"], currentDns=adapter["dns"] or _("không xác định"))

		dialog = wx.MessageDialog(
			self._active_dialog() or gui.mainFrame,
			message,
			action.title,
			style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
		)
		gui.mainFrame.prePopup()
		try:
			confirmed = dialog.ShowModal() == wx.ID_YES
		finally:
			dialog.Destroy()
			gui.mainFrame.postPopup()
		if confirmed:
			self._launch_elevated_action(action_id, provider_id, adapter)
		else:
			ui.message(_("Đã hủy."))

	def _launch_elevated_action(self, action_id, provider_id=None, adapter=None):
		try:
			script = _elevated_script_for_action(action_id, provider_id, adapter)
		except (KeyError, TypeError, ValueError):
			ui.message(_("Thông tin tác vụ không hợp lệ; tác vụ chưa được chạy."))
			return
		self._set_busy(True, _("Windows sẽ yêu cầu quyền quản trị. Đang chờ hoàn tất..."))
		ui.message(_("Windows sẽ yêu cầu quyền quản trị. Đang chạy tác vụ."))
		threading.Thread(
			target=self._elevated_action_worker,
			args=(action_id, provider_id, adapter, script),
			daemon=True,
		).start()

	def _elevated_action_worker(self, action_id, provider_id, adapter, script):
		try:
			exit_code, launch_error = _run_elevated_powershell(script)
			report, succeeded = _post_action_report(action_id, provider_id, adapter, exit_code, launch_error)
		except Exception as error:
			report = _("Không thể kiểm tra kết quả tác vụ: {}.").format(error)
			succeeded = False
		wx.CallAfter(self._finish_elevated_action, action_id, report, succeeded)

	def _finish_elevated_action(self, action_id, report, succeeded):
		if self._terminated:
			return
		status = _("Đã hoàn tất tác vụ.") if succeeded else _("Tác vụ không hoàn tất.")
		self._set_busy(False, status)
		dialog = self._active_dialog()
		if dialog:
			if action_id == "applyDns":
				dialog.append_result(report, status)
			else:
				dialog.show_result(report, status)
		ui.message(status)
