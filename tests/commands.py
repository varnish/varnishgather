import unittest

class TestBase(object):
    def setUp(self):
        if self.log is None:
            self.skipTest('Command output log is not present.')

    def test_banner(self):
        self.assertTrue(len(self.log) >= 3)
        if self.command not in str(self.log[1]):
            self.fail("'%s' not in '%s'" % (self.command, self.log[1]))

class TestRunCommand(TestBase, unittest.TestCase):
    pass

class TestRunPipeCommand(TestBase, unittest.TestCase):
    pass

class TestVarnishAdmCommand(TestBase, unittest.TestCase):
    def test_is_it_running(self):
        if len(self.log) > 5:
            self.skipTest('Varnish is running.')

        # when varnishadm is not running, we still expect the the varnishadm
        #   interface to return a stateful message.
        if 'Could not get hold of varnishd, is it running?' not in str(self.log[-1]):
            self.fail("Expected Varnishadm to provide a status message.")
