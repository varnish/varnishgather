import os
import unittest
import argparse
import tarfile

# We will run the following suite of tests against a varnishgather that was
#   generated on a single platform (e.g. debian:bullseye).
class TestVarnishGather(unittest.TestCase):
    target_gather = None
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
        # ['netstat -np','wc -l'],
        # "netstat -np | grep ESTABLISHED | wc -l"
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
        'semodule -l'
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
        'vadnishadm -- vcl.list',
        'vadnishadm -- param.show',
        'vadnishadm -- param.show changed',
        'vadnishadm -- purge.list',
        'vadnishadm -- ban.list',
        'vadnishadm -- debug.health',
        'vadnishadm -- backend.list',
        'vadnishadm -- panic.show',
    ]

    def setUp(self):
        self.tar = tarfile.open(self.target_gather, 'r:*')

    def tearDown(self):
        self.tar.close()

    def test(self):
        self.assertIsNotNone(self.tar)
        members = self.tar.getmembers()

        for command in self.commands:
            command_path = command.replace(' ','_').replace('/','_').replace('.','_')
            exists = None

            for member in members:
                if command_path in member.name:
                    exists = member
                    break

            if exists is None:
                # print("'%s' is not in the gather" % command_path)
                continue

            # if the output of the command does exist, we can test some things
            with self.subTest(exists.name):
                self.assertTrue(exists.isfile())
                buf = self.tar.extractfile(exists)
                self.assertIsNotNone(buf)
                lines = buf.readlines()
                # a banner should always be present
                self.assertTrue(len(lines) >= 3)
                if command not in str(lines[1]):
                    self.fail("Command banner for '%s' is missing" % command)
                # todo: expectations for cases, e.g.
                #   varnishd not running
                #   varnishlog timeout
                #   etc...

def main():
    parser = argparse.ArgumentParser(description='Test the output of varnishgather')
    parser.add_argument('target', type=str)
    args = parser.parse_args()

    for root, dirs, files in os.walk(args.target):
        for file in files:
            if 'varnishgather' in file:
                testclass = type('Test_%s' % root.split('/')[-1], (TestVarnishGather, ),
                    {'target_gather': os.path.join(root,file)})
                suite = unittest.TestLoader().loadTestsFromTestCase(testclass)
                unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    main()
