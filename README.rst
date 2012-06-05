Varnishgather
=============

Varnishgather is a simple script designed to gather as much relevant
information as possible on a Varnish Cache setup.

Primary platforms so far are Debian-based systems (including Ubuntu) and
RHEL-based systems (including centos, I suppose).

What does varnishgather gather
------------------------------

It gathers various statistics, metrics and facts about your system. It does
not under any circumstance transmit this information to others, it only
creates a tar-ball of it. It is up to you what to do with it.

The tar-ball currently contains two files: a raw ``varnishlog`` file, which
can be reviewed using ``varnishlog -r``, and a regular varnishgather log
file. The varnishgather log file contains most of the information,
including but not limited to:

* Any VCL files found in /etc/varnish/ (``*.vcl``, so
  ``/etc/varnish/secret`` is *not* included)
* Output of ``dmesg``, ``netstat``, ``ip``, ``iptables``, ``sysctl``,
  ``free``, ``vmstat``, ``df``, ``mount``, ``lsb_release``, ``uname`` and
  possibly similar commands. All with various information-gathering
  options.
* Any bans currently active
* Any loaded vcl.
* ``varnishstat -1`` output
* ``panic.show`` (on CLI) output

As varnishgather is sometimes updated to gather new data, the above list is
not meant to be complete, but an illustration of what to expect.

The data is intended to reveal everything and anything Varnish-related. Be
it whether or not network problems is causing latency, if cookies is being
treated safely, or if features like grace, streaming or ESI are set up
correctly.

Interpreting the data
---------------------

If there was an easy way to interpret the data, I would've written a script
called ``fixyourvarnishsetup`` instead ;)

There is no `howto` for interpreting the data, since there might be nothing
to interpret.

The only thing I can say is: use ``varnishlog -r`` to read the varnishlog
provided.

Are patches welcome?
--------------------

Yes.
