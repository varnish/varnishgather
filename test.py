import os
import re
import inspect
import unittest
import argparse
import tarfile
from tests.commands import TestRunCommand, TestRunPipeCommand, TestVarnishAdmCommand

class TestCommand(object):
    def __init__(self, cmd, test_class=TestRunCommand):
        self.cmd = cmd
        self.test_class = test_class

    def path(self):
        return re.sub(r'[\s\\/\.]', '_', self.cmd)

    def matches(self, file):
        if self.path() in file:
            return True
        return False

    def setup_test_case(self, root, log):
        platform = root.split('/')[-1]
        testclass = type("platform(%s), command(%s)" % (platform, self.path()), (self.test_class, ),{
            'command': self.cmd,
            'command_path': self.path(),
            'log': log
        })
        return unittest.TestLoader().loadTestsFromTestCase(testclass)

class TestSuiteGather(unittest.TestSuite):
    # For a given varnishgather that was run on a specific platform,
    #   this test suite will attempt to match each command with the related file.
    # Each command will have its own test case.
    # If a command can not be mached with a file, it is up to the test case to
    #   determine if that is a failure or not.
    def __init__(self, root, gather, commands, debug=False):
        super().__init__()
        self._debug("Setting up %s" % gather)
        self.gather = gather
        self.tar = tarfile.open(os.path.join(root,gather), 'r:*')
        self.debug = debug
        members = self.tar.getmembers()
        for c in commands:
            if type(c) == str:
                self._debug("Initializing command(%s) with defaults." % c)
                c = TestCommand(c)
            else:
                self._debug("Command(%s) already initalized." % c)
            exists = None

            for i, member in enumerate(members):
                log = member.name.split('/')[-1]
                if c.matches(log):
                    self._debug("    Command(%s) matched: %s" % (c.path(), log))
                    exists = members.pop(i)
                    break

            buf = None
            if exists is None:
                self._debug("   Unable to match")
            else:
                buf = self.tar.extractfile(exists)
                buf = buf.readlines()

            self.addTest(c.setup_test_case(root, buf))

    def __del__(self):
        self._debug("Cleaning up %s" % self.gather)
        self.tar.close()

    def _debug(self, *msg):
        if self.debug:
            print("DEBUG: %s" % msg)

def main():
    parser = argparse.ArgumentParser(description='Test the output of varnishgather')
    parser.add_argument('target', type=str)
    parser.add_argument('--debug', default=False, action="store_true")
    args = parser.parse_args()

    # A list of commands that are executed during a varnishgather and should be
    #   tested. Each command will be treated as an individual test suite that
    #   will default to using the "TestRunCommand" test case.
    commands = [
        'varnishd -V',
        'varnish-agent -V',
        'vha-agent -V',
        'broadcaster -V',
        'nats-server -v',
        'vcli version',
        'varnish-controller-brainz -version',
        'varnish-controller-agent -version',
        'varnish-controller-api-gw -version',
        'date',
        'varnish-controller-ui -version',
        'dmesg',
        'hostname',
        'cat /etc/hostname',
        'cat /var/log/dmesg',
        'cat /proc/cpuinfo',
        'cat /proc/version',
        'ps aux',
        'netstat -np',
        'uptime',
        'free -m',
        'ps axo',
        'vmstat',
        'mpstat',
        'iostat',
        'lsb_release -a',
        'cat /etc/redhat-release',
        'sysctl -a',
        'getenforce',
        'semodule -l',
        'semodule -lfull',
        'ausearch --context varnish --raw',
        'umask',
        'systemctl cat',
        'netstat -s',
        'ip a',
        'ip n',
        'ip r',
        'ip -s l',
        'ifconfig',
        'uname -a',
        'mount',
        'mount sort',
        'df -h',
        'fdisk -l',
        'lvdisplay -vm',
        'vgdisplay -v',
        'pvdisplay -v',
        'varnishstat -1',
        'varnishstat -j',
        #ldd "$(command -v varnishd)"
        #varnishadm ${VARNISHADMARG} debug.jemalloc_stats
        'varnishscoreboard'
        '/bin/netstat -nlpt',
        '/bin/netstat -np',
        'cat /etc/init.d/varnish',
        'cat /etc/default/varnish',
        'cat /etc/varnish/nats.conf',
        'cat /etc/sysconfig/varnish',
        'cat /etc/varnish/varnish.params',
        'cat /sys/kernel/mm/transparent_hugepage/enabled',
        'cat /sys/kernel/mm/redhat_transparent_hugepage/enabled',
        'cat /proc/user_beancounters',
        'cat /proc/meminfo',
        'cat /proc/crypto',
        'cat /proc/sys/net/ipv4/tcp_tw_reuse',
        #'cat /proc/$pid/cgroup',
        'cat /etc/sysconfig/vha-agent',
        'cat /etc/default/vha-agent',
        'cat /etc/init.d/vha-agent',
        'cat /etc/vha-agent/nodes.conf',
        'cat /etc/varnish/nodes.conf',
        'cat /var/lib/vha-agent/vha-status',
        'cat /etc/sysconfig/varnish-agent',
        'cat /etc/default/varnish-agent',
        'cat /etc/init.d/varnish-agent',
        'cat /var/lib/varnish-agent/agent.param',
        'cat /var/lib/varnish-agent/boot.vcl',
        'cat /etc/varnish/varnish-agent.params',
        'cat /etc/hitch/hitch.conf',
        'cat /etc/varnish/modsec/modsecurity.conf',
        'cat /etc/init.d/vac',
        'cat /opt/vac/etc/defaults',
        'cat /var/opt/vac/log/vac-stderr.log',
        'cat /var/opt/vac/log/vac.log',
        'cat /var/log/mongodb/mongodb.log',
        'cat /etc/sysconfig/vstatdprobe',
        'cat /etc/default/vstatdprobe',
        'cat /etc/init.d/vstatdprobe',
        'cat /etc/sysconfig/vstatd',
        'cat /etc/default/vstatd',
        'cat /etc/init.d/vstatd',
        'cat /etc/varnish/vstatd.params',
        'cat /etc/varnish/vstatdprobe.params',
        'cat /etc/hosts',
        'cat /etc/resolv.conf',
        'cat /etc/nsswitch.conf',
        'find /usr/local -name varnish',
        'find /var/lib/varnish -ls',
        'find /var/lib/varnish-agent -ls',
        'lsblk',
        'lspci -v -nn -k',
        TestCommand('varnishadm -- vcl.list', test_class=TestVarnishAdmCommand),
        TestCommand('varnishadm -- param.show', test_class=TestVarnishAdmCommand),
        TestCommand('varnishadm -- param.show changed', test_class=TestVarnishAdmCommand),
        TestCommand('varnishadm -- purge.list', test_class=TestVarnishAdmCommand),
        TestCommand('varnishadm -- ban.list', test_class=TestVarnishAdmCommand),
        TestCommand('varnishadm -- debug.health', test_class=TestVarnishAdmCommand),
        TestCommand('varnishadm -- backend.list', test_class=TestVarnishAdmCommand),
        TestCommand('varnishadm -- panic.show', test_class=TestVarnishAdmCommand)
    ]
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()
    for root, dirs, files in os.walk(args.target):
        for file in files:
            if 'varnishgather' not in file:
                # todo: this could be a failure condition
                continue
            suite.addTest(TestSuiteGather(root,file,commands,debug=args.debug))
    runner.run(suite)

if __name__ == '__main__':
    main()
