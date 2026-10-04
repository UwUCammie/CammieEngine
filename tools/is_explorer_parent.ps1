$ErrorActionPreference = 'SilentlyContinue'

$selfFilter = "ProcessId=$PID"
$self = Get-CimInstance -ClassName Win32_Process -Filter $selfFilter
if ($null -eq $self) {
	exit 0
}

for ($depth = 0; $depth -lt 12; $depth++) {
	$parentFilter = "ProcessId=$($self.ParentProcessId)"
	$parent = Get-CimInstance -ClassName Win32_Process -Filter $parentFilter
	if ($null -eq $parent) {
		break
	}
	if ($parent.Name -ine 'cmd.exe') {
		if ($parent.Name -ieq 'explorer.exe') {
			[Console]::Out.WriteLine('1')
		}
		break
	}
	$self = $parent
}
