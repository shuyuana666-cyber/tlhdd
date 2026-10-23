[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.-]*$')]
  [string]$Server,

  [Parameter(Mandatory = $true)]
  [Alias('User')]
  [ValidatePattern('^[A-Za-z_][A-Za-z0-9_-]*$')]
  [string]$SshUser,

  [ValidatePattern('^[A-Za-z_][A-Za-z0-9_-]*$')]
  [string]$ServiceUser = 'tlhdd',

  [ValidatePattern('^[A-Za-z_][A-Za-z0-9_-]*$')]
  [string]$ServiceName = 'tlhdd-v2',

  [ValidateRange(1024, 65535)]
  [int]$Port = 4174,

  [ValidatePattern('^/[A-Za-z0-9/_-]+$')]
  [string]$RemoteApp = '/srv/tlhdd',

  [string]$SshKeyPath
)

$ErrorActionPreference = 'Stop'

if ($RemoteApp.Contains('..')) {
  throw 'RemoteApp must not contain parent-directory segments.'
}
if ($ServiceUser -eq 'root') {
  throw 'The application service must run as a dedicated non-root user.'
}
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
  throw 'OpenSSH Client (ssh) is required.'
}
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
  throw 'OpenSSH Client (scp) is required.'
}
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python 3 is required to build the release archive.' }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$target = "$SshUser@$Server"
$sshArgs = @('-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15')
if ($SshKeyPath) {
  $key = (Resolve-Path $SshKeyPath).Path
  $sshArgs += @('-i', $key)
}

$releaseId = [Guid]::NewGuid().ToString('N')
$archive = Join-Path ([IO.Path]::GetTempPath()) "tlhdd-$releaseId.tar.gz"
$remoteArchive = "/tmp/tlhdd-$releaseId.tar.gz"
$remoteAppQuoted = "'$RemoteApp'"
$serviceUnit = @'
[Unit]
Description=Tonglihua Automotive Group website
After=network.target

[Service]
Type=simple
User=__SERVICE_USER__
WorkingDirectory=__REMOTE_APP__
EnvironmentFile=/etc/tlhdd/tlhdd.env
Environment=HOST=127.0.0.1
Environment=PORT=__PORT__
ExecStart=__REMOTE_APP__/.venv/bin/python __REMOTE_APP__/server.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=__REMOTE_APP__/data __REMOTE_APP__/uploads

[Install]
WantedBy=multi-user.target
'@
$serviceUnit = $serviceUnit.Replace('__SERVICE_USER__', $ServiceUser).Replace('__REMOTE_APP__', $RemoteApp).Replace('__PORT__', [string]$Port)
$serviceUnitB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($serviceUnit))

try {
  Write-Host 'Validating and creating a runtime-only release archive...'
  & $python.Source (Join-Path $repoRoot 'scripts/build_release.py') $archive
  if ($LASTEXITCODE -ne 0) { throw 'Could not create the release archive.' }

  Write-Host 'Uploading release archive with strict SSH host verification...'
  & scp @sshArgs $archive "${target}:$remoteArchive"
  if ($LASTEXITCODE -ne 0) { throw 'Could not upload the release archive.' }

  $remote = @"
set -eu
trap "rm -f '$remoteArchive'" EXIT
sudo mkdir -p /etc/tlhdd $remoteAppQuoted
test -f /etc/tlhdd/tlhdd.env || { echo 'Create /etc/tlhdd/tlhdd.env from deploy/tlhdd.env.example before deployment.' >&2; exit 2; }
id -u '$ServiceUser' >/dev/null 2>&1 || sudo useradd --system --home-dir $remoteAppQuoted --shell /usr/sbin/nologin '$ServiceUser'
sudo tar -xzf '$remoteArchive' -C $remoteAppQuoted
sudo mkdir -p $remoteAppQuoted/data $remoteAppQuoted/uploads
sudo chown -R root:root $remoteAppQuoted
sudo chown -R '${ServiceUser}:${ServiceUser}' $remoteAppQuoted/data $remoteAppQuoted/uploads
sudo chmod 755 $remoteAppQuoted
sudo chmod 750 $remoteAppQuoted/data
sudo find $remoteAppQuoted/uploads -type d -exec chmod 755 {} +
sudo python3 -m venv $remoteAppQuoted/.venv
sudo $RemoteApp/.venv/bin/pip install --disable-pip-version-check -r $RemoteApp/requirements.txt
printf '%s' '$serviceUnitB64' | base64 -d | sudo tee /etc/systemd/system/$ServiceName.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable '$ServiceName.service' >/dev/null
sudo systemctl restart '$ServiceName.service'
sleep 2
curl -fsS -I http://127.0.0.1:$Port/ >/dev/null
echo DEPLOY_OK
"@

  Write-Host 'Installing the service and checking the local health endpoint...'
  $sshArgsInteractive = $sshArgs + @('-t')
  & ssh @sshArgsInteractive $target $remote
  if ($LASTEXITCODE -ne 0) { throw "Remote deployment failed. Check systemctl status $ServiceName.service and its journal." }
  Write-Host "Deployment completed on $Server. Configure Nginx using deploy/nginx/tlhdd.cn.conf."
}
finally {
  Remove-Item -LiteralPath $archive -ErrorAction SilentlyContinue
}
