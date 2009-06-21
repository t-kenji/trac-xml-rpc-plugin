# -*- coding: utf-8 -*-
"""
License: BSD

(c) 2009      ::: www.CodeResort.com - BV Network AS (simon-code@bvnetwork.no)
"""

import unittest
import os
import shutil
import urllib2
from StringIO import StringIO

from tracrpc.web_ui import json

if json:
    from tracrpc.tests import rpc_testenv

    class JsonTestCase(unittest.TestCase):
        
        def _anon_req(self, data):
            req = urllib2.Request(rpc_testenv.url_anon_json,
                        headers={'Content-Type': 'application/json'})
            req.data = json.dumps(data)
            resp = urllib2.urlopen(req)
            return json.loads(resp.read())

        def _auth_req(self, data, user='user'):
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            handler = urllib2.HTTPBasicAuthHandler(password_mgr)
            password_mgr.add_password(realm=None,
                          uri=rpc_testenv.url_auth_json,
                          user=user,
                          passwd=user)
            req = urllib2.Request(rpc_testenv.url_auth_json,
                        headers={'Content-Type': 'application/json'})
            req.data = json.dumps(data)
            resp = urllib2.build_opener(handler).open(req)
            return json.loads(resp.read())

        def setUp(self):
            pass

        def tearDown(self):
            pass

        def test_call(self):
            result = self._anon_req(
                    {'method': 'system.listMethods', 'params': [], 'id': 244})
            self.assertTrue('system.methodHelp' in result['result'])
            self.assertEquals(None, result['error'])
            self.assertEquals(244, result['id'])

        def test_multicall(self):
            data = {'method': 'system.multicall', 'params': [
                    {'method': 'wiki.getAllPages', 'params': [], 'id': 1},
                    {'method': 'wiki.getPage', 'params': ['WikiStart', 1], 'id': 2},
                    {'method': 'ticket.status.getAll', 'params': [], 'id': 3},
                    {'method': 'nonexisting', 'params': []}
                ], 'id': 233}
            result = self._anon_req(data)
            self.assertEquals(4, len(result['result']))
            items = result['result']
            self.assertEquals(1, items[0]['id'])
            self.assertEquals(233, items[3]['id'])
            self.assertTrue('WikiStart' in items[0]['result'])
            self.assertEquals(None, items[0]['error'])
            self.assertTrue('Welcome' in items[1]['result'])
            self.assertEquals(['accepted', 'assigned', 'closed', 'new',
                                    'reopened'], items[2]['result'])
            self.assertEquals(None, items[3]['result'])
            self.assertEquals('JSONRPCError', items[3]['error']['name'])

        def test_datetime(self):
            # read and write datetime values
            from datetime import datetime
            from trac.util.datefmt import utc
            dt_str = "2009-06-19T16:46:00"
            dt_dt = datetime(2009, 06, 19, 16, 46, 00, tzinfo=utc)
            data = {'method': 'ticket.milestone.update',
                'params': ['milestone1', {'due': {'__jsonclass__':
                    ['datetime', dt_str]}}]}
            result = self._auth_req(data, user='admin')
            self.assertEquals(None, result['error'])
            result = self._auth_req({'method': 'ticket.milestone.get',
                'params': ['milestone1']}, user='admin')
            self.assertTrue(result['result'])
            self.assertEquals(dt_str,
                        result['result']['due']['__jsonclass__'][1])

        def test_binary(self):
            # read and write binaries values
            image_url = os.path.join(rpc_testenv.trac_src, 'trac',
                                 'htdocs', 'feed.png')
            image_in = StringIO(open(image_url, 'r').read())
            data = {'method': 'wiki.putAttachmentEx',
                'params': ['TitleIndex', "feed2.png", "test image",
                {'__jsonclass__': ['binary', 
                            image_in.getvalue().encode("base64")]}]}
            result = self._auth_req(data, user='admin')
            self.assertEquals('feed2.png', result['result'])
            # Now try to get the attachment, and verify it is identical
            result = self._auth_req({'method': 'wiki.getAttachment',
                            'params': ['TitleIndex/feed2.png']}, user='admin')
            self.assertTrue(result['result'])
            image_out = StringIO(
                    result['result']['__jsonclass__'][1].decode("base64"))
            self.assertEquals(image_in.getvalue(), image_out.getvalue())

        def test_xmlrpc_permission(self):
            # Test returned response if not XML_RPC permission
            rpc_testenv._tracadmin('permission', 'remove', 'anonymous',
                                    'XML_RPC')
            try:
                result = self._anon_req({'method': 'system.listMethods',
                                         'id': 'no-perm'})
                self.assertEquals(None, result['result'])
                self.assertEquals('no-perm', result['id'])
                self.assertEquals(-32600, result['error']['code'])
                self.assertTrue('XML_RPC' in result['error']['message'])
            finally:
                # Add back the default permission for further tests
                rpc_testenv._tracadmin('permission', 'add', 'anonymous',
                                            'XML_RPC')

        def test_method_not_found(self):
            result = self._anon_req({'method': 'system.doesNotExist',
                                     'id': 'no-method'})
            self.assertTrue(result['error'])
            self.assertEquals(result['id'], 'no-method')
            self.assertEquals(None, result['result'])
            self.assertEquals(-32603, result['error']['code'])
            self.assertTrue('not found' in result['error']['message'])

        def test_wrong_argspec(self):
            result = self._anon_req({'method': 'system.listMethods',
                            'params': ['hello'], 'id': 'wrong-args'})
            self.assertTrue(result['error'])
            self.assertEquals(result['id'], 'wrong-args')
            self.assertEquals(None, result['result'])
            self.assertEquals(-32603, result['error']['code'])
            self.assertTrue('listMethods() takes exactly 2 arguments' \
                                in result['error']['message'])

    def suite():
        return unittest.makeSuite(JsonTestCase)
else:
    print "SKIP: json not available. Cannot run tests."
    suite = unittest.TestSuite()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
