# Windows Notes for KIND and kubectl

Use these PowerShell forms instead of the Linux `curl`, `chmod`, and `sudo mv` commands.

## Install KIND

```powershell
$binDir = Join-Path $env:USERPROFILE "bin"
New-Item -ItemType Directory -Force $binDir | Out-Null

Invoke-WebRequest `
  -Uri "https://kind.sigs.k8s.io/dl/v0.22.0/kind-windows-amd64" `
  -OutFile (Join-Path $binDir "kind.exe")
```

Ensure `$binDir` is on `PATH` for the current shell:

```powershell
$env:PATH = "$binDir;$env:PATH"
```

## Install kubectl

```powershell
$version = (Invoke-RestMethod "https://dl.k8s.io/release/stable.txt").Trim()
Invoke-WebRequest `
  -Uri "https://dl.k8s.io/release/$version/bin/windows/amd64/kubectl.exe" `
  -OutFile (Join-Path $binDir "kubectl.exe")
```

## Create a Cluster

Docker Desktop must be running before creating a KIND cluster.

```powershell
kind create cluster
kubectl cluster-info
```
