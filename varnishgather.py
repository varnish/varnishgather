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
import re

os.environ["LC_ALL"] = "C"

HOSTNAME = os.uname()[1]
ID = "varnishgather-%s-%s" % (HOSTNAME, time.strftime("%Y-%m-%d"),)

simplecommands = (('date',),
                  ('dmesg',),
                  ('free', '-m',),
#                  ('vmstat', '5', '5',),
                  ('lsb_release', '-a',),
                  ('varnishstat', '-V',),
                  ('sysctl', '-a',),
                  ('dpkg', '-l', '*varnish*',),
                  ('netstat', '-s',),
                  ('ip', 'a',),
                  ('ip', 'n',),
                  ('ip', 'r',),
                  ('ip', '-s', 'l',),
                  ('uname', '-a',),
                  ('mount',),
                  ('df', '-h',),
                  ('netstat', '-nlpt',),
                  ('netstat', '-np',),
                  ('find', '/usr/local', '-name', 'varnish',),
                  ('grep', '-s', 'varnish', '/var/log/messages',),
                  ('grep', '-s', 'varnish', '/var/log/syslog',),
                  ('iptables', '-n', '-L',),
                  )

# Format is (command, filter, countonly)
filteredcommands = (
    (["ps", "aux"], lambda x: re.search(r'(varnish|apache|mysql|nginx|httpd|stud|stunnel)', x), False),
    (["rpm", "-qa"],  lambda x: re.search(r'varnish', x), False),
    (["netstat", "-np"], None, True,),
    (["netstat", "-np"], lambda x: re.search(r'ESTABLISHED', x), True,),
)

fileincludes = (
        '/var/log/dmesg',
        '/proc/cpuinfo',
        '/proc/version',
        '/etc/default/varnish',
        '/etc/sysconfig/varnish',
)

def filter_fname(name):
    f = lambda x: ("_", x)[x in string.ascii_letters + string.digits]
    return "".join(map(f, name))

def static_var(varname, value):
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate

@static_var("counter", 0)
def item():
    item.counter += 1
    return item.counter

itemnum = 0
class LoggedCommand:
    def __init__(self, cmd, prefix=ID, filter_stdout=None, only_count=False):
        self.command = cmd
        self.has_run = False
        self.output = None
        self.err_output = None
        self.filter_stdout = filter_stdout
        self.logfile = None
        self.prefix = prefix
        self.only_count = only_count

    def log_name(self):
        fname = filter_fname(" ".join(self.command))
        return os.path.join(self.prefix, "%.3d_%s" % (item(), fname,))

    def get_log(self):
        if self.logfile is None:
            self.logfile = StringIO.StringIO()
        self.logfile.write("=" * 79)
        self.logfile.write("\n")
        self.logfile.write("Command: %s\n" % (" ".join(self.command), ))
        self.logfile.write("=" * 79)
        self.logfile.write("\nSTDOUT:\n")
        self.logfile.write(self.output)
        self.logfile.write("\nSTDERR:\n")
        self.logfile.write(self.err_output)
        return self.logfile

    def run(self):
        try:
            p = Popen(self.command, stdout=PIPE, stderr=PIPE)
        except OSError, e:
            # program is not installed, cannot be found in $PATH, etc.
            self.output = ""
            self.err_output = str(e)
        else:
            stdoutlines = filter(self.filter_stdout, self.stdout.readlines())
            if self.only_count:
                stdoutlines = [str(len(stdoutlines))]
            self.output = "".join(stdoutlines)
            self.err_output = p.stderr.read()

    def __call__(self, tar = None):
        self.run()
        if tar:
            self.add_to_tarfile(tar)

    def add_to_tarfile(self, tar):
        tinfo = tarfile.TarInfo(name=self.log_name())
        tinfo.mtime = time.time()
        log = self.get_log()
        log.seek(0, os.SEEK_END)
        tinfo.size = log.tell()
        log.seek(0)
        tar.addfile(tinfo, log)

class FileInclude:
    def __init__(self, filename, prefix=ID):
        self.filename = filename
        self.prefix = prefix

    def __call__(self, tar=None):
        try:
            # Need to do this somewhat roundaboutish, since we include
            # files from /proc which aren't real files
            f = StringIO.StringIO()
            f.write(open(self.filename, "r").read())
            fname = "%.3d_%s" % (item(), filter_fname(self.filename))
            tinfo = tarfile.TarInfo(name=os.path.join(self.prefix, fname))
            tinfo.mtime = os.stat(self.filename).st_mtime
            f.seek(0, os.SEEK_END)
            tinfo.size = f.tell()
            f.seek(0)
            tar.addfile(tinfo, f)
        except IOError:
            # File didn't exist, most likely
            pass

def get_tarfile():
    outfile = "%s.tar.gz" % (ID,)
    tar = tarfile.open(outfile, "w:gz")
    return tar

tar = get_tarfile()

for cmd in simplecommands:
    print "Running %s" % (" ".join(cmd))
    LoggedCommand(cmd)(tar)

for (cmd, filter_stdout, only_count) in filteredcommands:
    print "Running filtered %s %s" % (" ".join(cmd), filter_stdout)
    LoggedCommand(cmd, filter_stdout=filter_stdout, only_count=only_count)(tar)

print "Including files"
for f in fileincludes:
    FileInclude(f)(tar)

tar.close()

print "=" * 79
print "Please submit the file:\n%s" % (tar.name,)
print "=" * 79

#run varnishstat -1 $STATCMD


#for a in $(findvcls); do
#	mycat $a
#done

#mycat /proc/$(pgrep -n varnishd)/limits

#for pid in $(pidof varnishd); do
#    runpipe "awk '$2 ~ \"rw\"' /proc/$pid/maps" "wc -l"
#done

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
