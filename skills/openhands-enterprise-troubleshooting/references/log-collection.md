# OHE VM Log Collection

Use this workflow to send logs from a Replicated VM installation to the customer's observability platform. For one-off diagnostics, collect a support bundle instead.

## Log Locations

Application logs are written under `/var/log/pods` using this layout:

```text
/var/log/pods/<namespace>_<pod>_<pod-id>/<container>/<restart-count>.log
```

`/var/log/containers` contains symlinks with pod, namespace, container, and container ID in each filename:

```text
/var/log/containers/<pod>_<namespace>_<container>-<container-id>.log
```

Also collect:

- the systemd journal for cluster and operating system logs;
- `/var/log/embedded-cluster/` for installation and upgrade output.

The application log files are readable only by `root`. Current files end in `.log`; rotated files have a timestamp suffix and are compressed. A `*.log` pattern collects current output and skips rotated copies.

## Continuous Collection

1. Install the observability platform's Linux log agent on every VM, including VMs that run sandboxes.
2. Run the agent as `root`.
3. Configure a file input for `/var/log/pods/*/*/*.log`, or `/var/log/containers/*.log` when the agent reads Kubernetes symlinks.
4. Enable the agent's CRI parser. Each line starts with a timestamp and stream marker, while the message is JSON.
5. Enable the agent's journald input.
6. Set retention in the observability platform and confirm that recent records arrive.

Verify with one recent application line:

```bash
sudo sh -c 'tail -n 1 /var/log/pods/openhands_openhands-*/openhands/*.log'
```

A VM holds only logs for services running on that VM. The VM retains roughly 50 MB per service, and sandbox logs are deleted when the associated conversation is cleaned up. Continuous collection is required when evidence must outlive those limits.

Official reference: https://docs.openhands.dev/enterprise/vm-install/log-collection
