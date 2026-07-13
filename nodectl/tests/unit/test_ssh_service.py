from __future__ import annotations

import paramiko

from backend.services.ssh import SSHService


class FakeSSHClient:
    def __init__(self):
        self.loaded_host_keys = None
        self.policy = None
        self.connect_kwargs = None

    def load_host_keys(self, path):
        self.loaded_host_keys = path

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs

    def exec_command(self, command, timeout):
        class Channel:
            def recv_exit_status(self):
                return 0

        class Reader:
            def __init__(self, data):
                self._data = data
                self.channel = Channel()

            def read(self):
                return self._data

        return None, Reader(b""), Reader(b"")

    def close(self):
        return None


def test_factory_ssh_uses_injected_key_and_known_hosts(app_settings, monkeypatch):
    fake_client = FakeSSHClient()
    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_client)
    service = SSHService(app_settings)
    target = service.factory_target()

    service.run(target, ["true"])

    assert fake_client.loaded_host_keys == str(app_settings.ssh_known_hosts_path)
    assert isinstance(fake_client.policy, paramiko.RejectPolicy)
    assert fake_client.connect_kwargs["key_filename"] == str(app_settings.factory_ssh_key_path)
    assert fake_client.connect_kwargs["look_for_keys"] is False
    assert fake_client.connect_kwargs["allow_agent"] is False


def test_vm_ssh_honors_configured_user_port_key_and_known_hosts(app_settings, monkeypatch):
    fake_client = FakeSSHClient()
    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_client)
    service = SSHService(app_settings)
    target = service.vm_target(node_id="vm-01", host="10.0.0.10", user="ubuntu", port=2202)

    service.run(target, ["true"])

    assert fake_client.connect_kwargs["hostname"] == "10.0.0.10"
    assert fake_client.connect_kwargs["port"] == 2202
    assert fake_client.connect_kwargs["username"] == "ubuntu"
    assert fake_client.connect_kwargs["key_filename"] == str(app_settings.vm_ssh_key_path)


def test_ssh_service_never_falls_back_to_home_directory_keys(app_settings, monkeypatch):
    fake_client = FakeSSHClient()
    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_client)
    service = SSHService(app_settings)

    service.run(service.factory_target(), ["true"])

    assert fake_client.connect_kwargs["look_for_keys"] is False
    assert fake_client.connect_kwargs["allow_agent"] is False
