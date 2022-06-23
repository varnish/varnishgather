import os
import inspect
import unittest
import argparse
import tarfile

# Generic test class for run commands
class TestRunCommand(unittest.TestCase):
    def setUp(self):
        if self.buf is None:
            self.skipTest('Command output is not present.')

        self.lines = self.buf.readlines()

    def test_exists(self):
        self.assertIsNotNone(self.buf)

    def test_banner(self):
        self.assertTrue(len(self.lines) >= 3)
        if self.command not in str(self.lines[1]):
            self.fail("'%s' not in '%s'" % (self.command, self.lines[1]))

class TestRunPipeCommand(unittest.TestCase):
    def test_exists(self):
        self.assertIsNotNone(self.buf)

class Command(object):
    def __init__(self, cmd, test_class=TestRunCommand):
        self.cmd = cmd
        self.test_class = test_class

    def path(self):
        # todo: regex
        return self.cmd.replace(' ','_').replace('/','_').replace('.','_')

    def matches(self, file):
        if self.path() in file:
            return True
        return False

    def setup_test_case(self, root, buf):
        platform = root.split('/')[-1]
        testclass = type("%s_%s" % (platform, self.path()), (self.test_class, ),{
            'command': self.cmd,
            'command_path': self.path(),
            'buf': buf
        })
        return unittest.TestLoader().loadTestsFromTestCase(testclass)

class TestSuiteGather(unittest.TestSuite):
    def __init__(self, root, gather, commands):
        super().__init__()
        self.tar = tarfile.open(os.path.join(root,gather), 'r:*')
        members = self.tar.getmembers()
        for c in commands:
            if type(c) == str:
                c = Command(c)
            exists = None

            for i, member in enumerate(members):
                if c.matches(member.name):
                    exists = members.pop(i)
                    break

            buf = None
            if exists is not None:
                buf = self.tar.extractfile(exists)

            self.addTest(c.setup_test_case(root, buf))

    def __del__(self):
        self.tar.close()

def main():
    parser = argparse.ArgumentParser(description='Test the output of varnishgather')
    parser.add_argument('target', type=str)
    args = parser.parse_args()

    # A list of commands that are executed during a varnishgather. 
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
        Command('ps aux', test_class=TestRunPipeCommand),
        Command('netstat -np', test_class=TestRunPipeCommand),
        'uptime',
        'free -m',
        Command('ps axo', test_class=TestRunPipeCommand),
        'vmstat',
        'mpstat',
        'iostat',
        'lsb_release -a',
        'cat /etc/redhat-release',
        'sysctl -a',
        'getenforce',
        Command('semodule -l', test_class=TestRunPipeCommand),
        Command('semodule -lfull', test_class=TestRunPipeCommand),
        Command('ausearch --context varnish --raw', test_class=TestRunPipeCommand),
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
        'vadnishadm -- vcl.list',
        'vadnishadm -- param.show',
        'vadnishadm -- param.show changed',
        'vadnishadm -- purge.list',
        'vadnishadm -- ban.list',
        'vadnishadm -- debug.health',
        'vadnishadm -- backend.list',
        'vadnishadm -- panic.show',
    ]
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()
    for root, dirs, files in os.walk(args.target):
        for file in files:
            if 'varnishgather' not in file:
                # todo: this could be a failure condition
                continue
            suite.addTest(TestSuiteGather(root,file,commands))
    runner.run(suite)

if __name__ == '__main__':
    main()
