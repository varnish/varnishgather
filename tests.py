import os
import unittest
import argparse
import tarfile

class TestVarnishGather(unittest.TestCase):
    target_gather = None

    def setUp(self):
        self.tar = tarfile.open(self.target_gather, 'r|gz')

    def tearDown(self):
        self.tar.close()

    def test_tar_exists(self):
        self.assertIsNotNone(self.tar)

def main():
    parser = argparse.ArgumentParser(description='Test the output of varnishgather')
    parser.add_argument('target', type=str)
    args = parser.parse_args()

    print(args.target)
    for root, dirs, files in os.walk(args.target):
        for file in files:
            if 'varnishgather' in file:
                testclass = type('Test_%s' % root.split('/')[-1], (TestVarnishGather, ),
                    {'target_gather': os.path.join(root,file)})
                suite = unittest.TestLoader().loadTestsFromTestCase(testclass)
                unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    main()
