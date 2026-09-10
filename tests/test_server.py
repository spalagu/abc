import http.client
import json
from pathlib import Path
import threading
import time
import unittest
from continuity.core import Problem, Window
from continuity.fixture import FixtureAdapter
from continuity.server import Engine, make_server

C1='1'*32
C2='2'*32


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.adapter = FixtureAdapter()
        self.e = Engine(self.adapter)
        self.e.dispatch(C1, '/api/select', {'window':101})
        self.e.dispatch(C1, '/api/claim', {})

    def act(self, revision, rid='a'*32, **extra):
        data={'request_id':rid,'mode':'semantic','action':'press','node':'2','revision':revision}
        data.update(extra)
        return self.e.dispatch(C1,'/api/action',data)

    def snapshot(self):
        return self.e.dispatch(C1,'/api/semantics',{})

    def test_single_controller(self):
        with self.assertRaises(Problem):self.e.dispatch(C2,'/api/claim',{})
        self.e.dispatch(C1,'/api/release',{})
        self.assertTrue(self.e.dispatch(C2,'/api/claim',{})['control'])

    def test_no_control_no_side_effect(self):
        snap=self.snapshot()
        self.e.dispatch(C1,'/api/release',{})
        with self.assertRaises(Problem):self.act(snap['revision'])
        self.assertEqual(self.adapter.clicks,0)

    def test_same_action_replay_is_deduplicated(self):
        revision=self.snapshot()['revision']
        self.assertFalse(self.act(revision)['replay'])
        self.assertTrue(self.act(revision)['replay'])
        self.assertEqual(self.adapter.clicks,1)
        with self.assertRaises(Problem):self.act(revision, action='set',text='different')

    def test_stale_snapshot_refused(self):
        old=self.snapshot()['revision']
        self.snapshot()
        with self.assertRaises(Problem):self.act(old)
        self.assertEqual(self.adapter.clicks,0)

    def test_changed_native_value_refused(self):
        snap=self.snapshot()
        self.adapter.value='Changed on host'
        with self.assertRaises(Problem):self.act(snap['revision'], action='set',node='1',text='overwrite')
        self.assertEqual(self.adapter.value,'Changed on host')

    def test_new_viewer_observes_same_host_work(self):
        snap=self.snapshot()
        self.act(snap['revision'],action='set',node='1',text='Unsubmitted host draft')
        self.e.dispatch(C2,'/api/select',{'window':101})
        result=self.e.dispatch(C2,'/api/semantics',{})
        self.assertEqual(result['nodes'][1]['value'],'Unsubmitted host draft')
        self.assertEqual(self.e.sessions[C1].window.identity,self.e.sessions[C2].window.identity)

    def test_recycled_window_identity_is_not_followed(self):
        self.adapter.window=Window(101,123,'another-process','TEST','New',(0,0,960,640))
        with self.assertRaises(Problem):self.snapshot()

    def test_frame_budget_shared_between_clients(self):
        self.e.budget.limit=1
        for client in (C1,C2):
            self.e.dispatch(client,'/api/select',{'window':101})
            with self.assertRaises(Problem):self.e.dispatch(client,'/api/frame',{})
        self.assertEqual(self.e.budget.used,0)
        self.assertEqual(self.e.budget.blocked,2)
        self.assertEqual(self.e.sessions[C1].frames.revision,'')
        self.assertTrue(self.snapshot()['nodes'])

    def test_visual_action_requires_fresh_frame(self):
        self.e.dispatch(C1,'/api/frame',{})
        revision=self.e.sessions[C1].frames.revision
        self.e.dispatch(C1,'/api/action',{'request_id':'a'*32,'action':'click','revision':revision,'x':.5,'y':.5})
        with self.assertRaises(Problem):
            self.e.dispatch(C1,'/api/action',{'request_id':'b'*32,'action':'click','revision':revision,'x':.5,'y':.5})
        self.assertEqual(self.adapter.clicks,1)

    def test_revoke_stops_existing_session(self):
        self.e.revoke()
        with self.assertRaises(Problem): self.snapshot()
        self.assertEqual(self.e.sessions, {})

    def test_invalid_inputs(self):
        for x in [None, True, '101', [], {}]:
            with self.subTest(x=x), self.assertRaises(Problem):self.e.dispatch(C1,'/api/select',{'window':x})
        with self.assertRaises(Problem):self.e.dispatch('invalid','/api/status',{})
        with self.assertRaises(Problem):self.e.dispatch(C1,'/api/unknown',{})


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server(FixtureAdapter(),Path(__file__).resolve().parents[1]/'web',port=0)
        cls.port=cls.server.server_address[1]
        cls.origin=f'http://127.0.0.1:{cls.port}'
        cls.server.origins={cls.origin}
        cls.server.authorities={f'127.0.0.1:{cls.port}'}
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,path='/api/status',body='{}',auth=True,extra=None,method='POST'):
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        headers={'Content-Type':'application/json','X-WC-Client':C1}
        if auth:headers['Authorization']='Bearer '+self.server.engine.token
        headers.update(extra or {})
        c.request(method,path,body=body,headers=headers)
        r=c.getresponse();data=r.read();status=r.status;h=dict(r.getheaders());c.close()
        return status,data,h

    def test_auth_is_required(self):
        self.assertEqual(self.request(auth=False)[0],401)
        self.assertEqual(self.request()[0],200)

    def test_cross_origin_blocked(self):
        self.assertEqual(self.request(extra={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request(extra={'Sec-Fetch-Site':'cross-site'})[0],403)

    def test_dns_rebinding_host_blocked(self):
        self.assertEqual(self.request(extra={'Host':'evil.example'})[0],403)

    def test_bad_and_oversized_json(self):
        for body in ['{','[]','{"x":NaN}']:
            self.assertEqual(self.request(body=body)[0],400)
        self.assertEqual(self.request(body='x'*50000)[0],413)

    def test_static_page_has_no_token_and_no_cache(self):
        status,data,h=self.request(path='/',method='GET',body=None,auth=False)
        self.assertEqual(status,200)
        self.assertNotIn(self.server.engine.token.encode(),data)
        self.assertEqual(h['Cache-Control'],'no-store')
        self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
        self.assertEqual(self.request(path='/../host.py',method='GET',body=None)[0],404)
