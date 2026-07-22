Varnishgather
=============

varnishgather is a simple script designed to gather as much relevant
information as possible on a Varnish Cache setup.

Primary platforms so far are Debian-based systems (including Ubuntu) and
RHEL-based systems (including CentOS/other derivatives.).

Usage
------
::

  wget -N https://raw.githubusercontent.com/varnish/varnishgather/master/varnishgather
  sudo sh ./varnishgather
  


What does varnishgather gather
------------------------------

Varnishgather gathers various statistics, metrics and facts about your system.
These are output into a .tar.gz archive file. It is up to you what to do with it.

The tar-ball currently contains a set of text files for different
probes or tests, and a small raw ``varnishlog`` file which can be reviewed
using ``varnishlog -r``.

The probes/tests include information similar to:

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

A detailed guide on how to interpret a gather ships as a Claude Code skill
(see the next section).

Analyzing a gather with Claude Code
-----------------------------------

The repository ships a Claude Code skill
(``skills/analyze-varnishgather/``) that knows how to read a gather and
produce a diagnostic report, including helper scripts for the automated
warning checklist (``vg-check``) and for reading the raw log
(``vg-log``).

Install it by symlinking it into your personal skills directory, so
updates arrive with ``git pull``::

  git clone https://github.com/varnish/varnishgather.git
  mkdir -p ~/.claude/skills
  ln -s "$PWD/varnishgather/skills/analyze-varnishgather" ~/.claude/skills/

To update::

  git -C varnishgather pull

If you copied the directory instead of symlinking, re-run the copy
after pulling.

Then, from a directory containing an extracted gather (or the
tarball)::

  claude "analyze this varnishgather"

Are patches welcome?
--------------------

Yes.
