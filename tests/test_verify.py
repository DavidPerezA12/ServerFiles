"""Run the verifier against simulated host states, without touching the host."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify.sh'


class VerifyTests(unittest.TestCase):
    def run_verifier(self, *, backend='Running', power=None, login_error=False,
                     status=None, role='server', monitoring=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = {
                'hostname': 'echo fixture-mini', 'id': 'echo fixture',
                'sysctl': 'echo Macmini9,1', 'uname': 'echo arm64',
                'defaults': 'echo fixture', 'fdesetup': 'echo "FileVault is Off."',
                'pmset': power if power is not None else 'printf " sleep 0\\n autorestart 1\\n womp 1\\n"',
                'nc': 'exit 0',
                'tailscale': "cat <<'JSON'\n" + (status if status is not None else json.dumps({'BackendState': backend})) + '\nJSON',
                'curl': ('case "$*" in *http_code*) printf 200;; esac' if monitoring else 'exit 7'),
                'osascript': 'exit 1' if login_error else 'echo /Applications/Example.app',
            }
            for name, body in tools.items():
                path = root / name
                path.write_text('#!/bin/sh\n' + body + '\n')
                path.chmod(0o755)
            (root / 'python3').symlink_to(sys.executable)
            env = dict(os.environ, PATH=str(root) + ':/usr/bin:/bin',
                       SERVERFILES_TAILSCALE_CLI=str(root / 'tailscale'))
            return subprocess.run(['/bin/sh', str(SCRIPT), '--role', role],
                                  env=env, text=True, capture_output=True, timeout=10)

    def test_healthy_server(self):
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Tailscale backend Running', result.stdout)

    def test_successful_cli_exit_with_stopped_backend_is_failure(self):
        result = self.run_verifier(backend='Stopped')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL  Tailscale backend Stopped', result.stdout)
        self.assertNotIn('ok    Tailscale', result.stdout)

    def test_invalid_status_is_not_connected(self):
        result = self.run_verifier(status='not JSON')
        self.assertIn('FAIL  cannot read Tailscale backend state', result.stdout)
        self.assertNotEqual(result.returncode, 0)

    def test_failed_or_empty_power_read_is_not_ok(self):
        for power in ['exit 1', 'exit 0']:
            with self.subTest(power=power):
                result = self.run_verifier(power=power)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('ok    sleep 0', result.stdout)

    def test_denied_login_item_read_is_not_ok(self):
        result = self.run_verifier(login_error=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL  cannot read login items', result.stdout)
        self.assertNotIn('ok    no broken login items', result.stdout)

    def test_server_does_not_silently_skip_missing_monitoring(self):
        result = self.run_verifier(monitoring=False)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn('FAIL  Netdata not answering', result.stdout)
        self.assertIn('FAIL  Stats panel not answering', result.stdout)

    def test_client_skips_server_requirements(self):
        result = self.run_verifier(role='client', power='exit 1', monitoring=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('skip  Netdata and Stats', result.stdout)


if __name__ == '__main__':
    unittest.main()
