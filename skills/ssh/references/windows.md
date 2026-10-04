# Windows Notes for SSH Commands

Windows includes OpenSSH Client on current Windows versions. Use these PowerShell forms for Windows-native setup.

## Key Paths

Use the Windows profile path:

```powershell
$sshDir = Join-Path $env:USERPROFILE ".ssh"
New-Item -ItemType Directory -Force $sshDir | Out-Null
```

## Generate and Use a Key

```powershell
$key = Join-Path $sshDir "key_name"
ssh-keygen -t ed25519 -f $key -C "comment" -N ""
ssh -i $key username@hostname
```

## Create SSH Config

```powershell
$config = Join-Path $sshDir "config"
@'
Host alias
    HostName hostname_or_ip
    User username
    IdentityFile ~/.ssh/key_name
    Port 22
    ServerAliveInterval 60
'@ | Set-Content -LiteralPath $config -Encoding ascii
```

## Start ssh-agent

```powershell
Set-Service ssh-agent -StartupType Automatic
Start-Service ssh-agent
ssh-add $key
```

## Permissions

POSIX `chmod 600` does not apply to Windows filesystems. Restrict private-key ACLs with `icacls`:

```powershell
icacls $key /inheritance:r
icacls $key /grant:r "${env:USERNAME}:R"
```

## Copy a Public Key

`ssh-copy-id` is usually not installed on Windows. For Unix-like remotes, append the key with SSH:

```powershell
Get-Content "$key.pub" | ssh username@hostname "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```
