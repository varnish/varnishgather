#!/bin/sh
# varnish_gather - Gather debug information for varnish issues
# Copyright (C) 2010 Kristian Lyngstol <kristian@bohemians.org>
# Copyright (C) 2011 Varnish Software AS
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Version: 1.0
# Date: Fri Apr  8 13:16:26 CEST 2011
#
#
# Mostly harmless.

HOSTPORT="localhost:6082"
SECRET=""
ITEM=0
TOPDIR="$(mktemp -d /tmp/varnishgather.XXXXXXXX)"
DIR="${TOPDIR}/varnishgather"
mkdir -p ${DIR}
LOG="${DIR}/varnishgather.log"
ORIGPWD=$PWD
cd ${DIR}

log()
{
	echo >>${LOG} "$*"
}

info()
{
	echo 1>&2 "$*"
	log "$*"
}

banner()
{
	log "--------------------------------"
	log "Item $ITEM: $*"
	log
	ITEM=$(( $ITEM + 1 ))
	echo "Task: ${ITEM}: $*"
}

run()
{
	banner "$*"
	$* >> ${LOG}
}

mycat()
{
	if [ -r $1 ]; then
		run cat $1
	fi
}

getarg() {
	ret=""
	for a in `pidof varnishd`; do
		tmpret=$(awk -v RS='[[:cntrl:]]' -v arg=$1 's == 1 { sec=$0 }; $0 == arg {s=1}$0 != arg  {s=0} END { print sec };' /proc/${a}/cmdline)
		if [ x$ret != "x" ] && [ $ret != $tmpret ]; then
			log "Weird argument mismatch: $ret vs $tmpret found"
			info "(Using last found/listed)"
		fi
		ret=${tmpret}
	done
	echo ${ret}
}

HOSTPORT=$(getarg -T)
if [ -z "$HOSTPORT" ]; then
	info "Without a hostname:port for the admin interface, this script is less useful"
else
	banner "Found hostport(-T argument): ${HOSTPORT}"
fi

sec=$(getarg -S)
if [ ! -z ${sec} ]; then
	if [ -r ${sec} ]; then
		banner "Found secretfile(-S argument) ${sec} and it's readable. Using it."
		SECRET="-S ${sec}"
	elif [ -f /etc/varnish/secret ]; then
		banner "Found secretfile(-S argument) ${sec} but it's not readable"
	fi
else
	banner "Didn't find any -S argument"
fi

VARNISHADMARG="${SECRET} -T ${HOSTPORT}"
banner "Complete varnishadm command line deduced to: ${VARNISHADMARG}"
run dmesg
mycat /var/log/dmesg

for a in /var/log/messages /var/log/syslog; do
	if [ -r $a ]; then
		run grep varnish $a
	fi
done

mycat /proc/cpuinfo
mycat /proc/version

run free -m
run vmstat 5 5
banner "ps aux | egrep '(varnish|apache|mysql|nginx|httpd)'"
ps aux | egrep '(varnish|apache|mysql|nginx|httpd)' >> ${LOG}
run varnishstat -1

if [ ! -z "$2" ]; then
	run varnishstat -1 -n $2
fi

run mount

NETSTAT="/bin/netstat"
if [ -x "$NETSTAT" ]; then
	run ${NETSTAT} -nlpt
	run ${NETSTAT} -np
fi

mycat /etc/default/varnish
mycat /etc/sysconfig/varnish

run find /usr/local -name varnish

if [ ! -z "${VARNISHADMARG}" ]; then
	run varnishadm ${VARNISHADMARG} vcl.list
	run varnishadm ${VARNISHADMARG} vcl.show boot
	run varnishadm ${VARNISHADMARG} param.show
	run varnishadm ${VARNISHADMARG} purge.list
else
	banner "NO ADMINPORT SUPPLIED"
fi
run varnishlog -d -k 200 -w ${DIR}/varnishlog.raw
banner "End"
cd ${TOPDIR}
DATE="$(date +%Y-%m-%d-%H%M%S)"
tar czf ${TOPDIR}/varnishgather.tar.gz varnishgather/
echo Log: ${LOG}
cd $ORIGPWD
copyto="varnishgather.${DATE}.log"
if [ ! -f $copyto ]; then
	cp ${LOG} $copyto || exit 1
	echo "Log is in ${copyto}."
fi
copytogz="varnishgather.${DATE}.tar.gz"
if [ ! -f $copytogz ]; then
	cp ${TOPDIR}/varnishgather.tar.gz $copytogz || exit 1
	echo "Data to submit: $copyto (includes log)"
	echo " You can delete the workdir: rm -r ${TOPDIR}"
fi

