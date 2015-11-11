import sys
import os
import unittest
import cStringIO

import buildpath_to_syspath
print(sys.path)
import mipp.cfg

datadir = (os.path.dirname(__file__) or '.') + '/data'

class Test(unittest.TestCase):

    def test_config_parser(self):
        cfgfile = 'msg2'        
        os.environ['PPP_CONFIG_DIR'] = datadir
        c = mipp.cfg.read_config(cfgfile)
        fp = cStringIO.StringIO()
        for name in ('satellite', 'level1', 'level2'):
            h = c(name)
            print(name, file=fp)
            for k in sorted(h.keys()):
                print('    ', k + ':',  h[k], file=fp)
        print(mipp.cfg._Channel(c(1).items()), file=fp)
        print(mipp.cfg._Channel(c(2).items()), file=fp)
        print(mipp.cfg._Channel(c(3).items()), file=fp)
        for name in c.channel_names:
            print(c.get_channel(name), file=fp)
        text1 = fp.getvalue().strip()
        fp.close()
        fp = open(datadir + '/' + cfgfile + '.cfg.out')
        text2 = fp.read().strip()
        fp.close()
        self.assertTrue(text1 == text2, msg='Reading %s.cfg failed'%cfgfile)

if __name__ == '__main__':
    unittest.main()

    
