#! /usr/bin/python

import os
import tempfile
import atexit
import shutil
import string
from subprocess import Popen, PIPE
import tarfile
import time
import cStringIO as StringIO

os.environ["LC_ALL"] = "C"

HOSTNAME = os.uname()[1]
ID = "varnishgather-%s-%s" % (HOSTNAME, time.strftime("%Y-%m-%d"),)
class LoggedCommand:
    num = 0

    def __init__(self, cmd, prefix=ID, filter=None):
        self.order = LoggedCommand.num
        LoggedCommand.num += 1
        self.command = cmd
        self.has_run = False
        self.stdout = None
        self.stderr = None
        self.filter = filter
        self.logfile = None
        self.prefix = prefix

    def log_name(self):
        f = lambda x: ("_", x)[x in string.ascii_letters + string.digits]
        fname = "".join(map(f, " ".join(self.command)))
        return os.path.join(self.prefix, "%.3d_%s" % (self.order, fname,))

    def get_log(self):
        if self.logfile is None:
            self.logfile = StringIO.StringIO()
        self.logfile.write("=" * 79)
        self.logfile.write("\n")
        self.logfile.write("Command: %s\n" % (" ".join(self.command), ))
        self.logfile.write("=" * 79)
        self.logfile.write("\nSTDOUT:\n")
        self.logfile.write(self.stdout.read())
        self.logfile.write("\nSTDERR:\n")
        self.logfile.write(self.stderr.read())
        return self.logfile

    def run(self):
        p = Popen(self.command, shell=True, stdout=PIPE, stderr=PIPE)
        self.stdout = p.stdout
        self.stderr = p.stderr

    def __call__(self, tar = None):
        self.run()
        if tar:
            self.add_to_tarfile(tar)

    def add_to_tarfile(self, tar):
        tinfo = tarfile.TarInfo(name=self.log_name())
        log = self.get_log()
        log.seek(0, os.SEEK_END)
        tinfo.size = log.tell()
        log.seek(0)
        tar.addfile(tinfo, log)

def get_tarfile():
    outfile = "%s.tar.gz" % (ID,)
    tar = tarfile.open(outfile, "w:gz")
    return tar

tar = get_tarfile()

LoggedCommand(["date"])(tar)
LoggedCommand(["dmesg"])(tar)

tar.close()

print "=" * 79
print "Please submit the file:\n%s" % (tar.name,)
print "=" * 79

#mycat /var/log/dmesg

#for a in /var/log/messages /var/log/syslog; do
#	if [ -r "$a" ]; then
#		run grep varnish "$a"
#	fi
#done

#mycat /proc/cpuinfo
#mycat /proc/version

#runpipe "ps aux" "egrep (varnish|apache|mysql|nginx|httpd|stud|stunnel)"
#runpipe "netstat -np" "wc -l"
#runpipe "netstat -np" "grep ESTABLISHED" "wc -l"
#run free -m
#run vmstat 5 5
#run lsb_release -a
#run sysctl -a
#run varnishstat -V
#run dpkg -l \*varnish\*
#runpipe "rpm -qa" "grep varnish"
#run netstat -s
#run ip a
#run ip n
#run ip r
#run ip -s l
#run uname -a
#run mount
#run df -h
#run varnishstat -1 $STATCMD

#NETSTAT="/bin/netstat"
#if [ -x "$NETSTAT" ]; then
#	run "${NETSTAT}" -nlpt
#	run "${NETSTAT}" -np
#fi

#run iptables -n -L

#for a in $(findvcls); do
#	mycat $a
#done

#mycat /etc/default/varnish
#mycat /etc/sysconfig/varnish
#mycat /proc/$(pgrep -n varnishd)/limits

#for pid in $(pidof varnishd); do
#    runpipe "awk '$2 ~ \"rw\"' /proc/$pid/maps" "wc -l"
#done

#run find /usr/local -name varnish

#if [ -z "${VARNISHADMARG}" ]; then
#	banner "NO ADMINPORT SUPPLIED OR FOUND"
#fi

# vadmin() tests for VARNISHADMARG as necessary

#vadmin vcl.list
#vcls="$(vadmin_getvcls)"
#if [ -n "$vcls" ]; then
# 	for vcl in $vcls; do
# 		vadmin vcl.show "$vcl"
# 	done
# fi

# vadmin param.show
# vadmin purge.list
# vadmin ban.list
# vadmin debug.health
# vadmin panic.show

# run varnishlog -d -k 20000 -w "${DIR}/varnishlog.raw" $STATCMD

# XXX: option handling
